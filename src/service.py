# -*- coding: utf-8 -*-
"""业务逻辑层

实现全部业务规则：成绩合法性校验、总评与绩点计算、成绩册初始化、
成绩的增删改查与统计、用户权限判断、数据备份恢复。
对应实验二构件图中的业务逻辑层构件，以及类图中的 GradeManager 控制类。
"""
import os
import shutil
from datetime import datetime

import dao

# 总评成绩权重，平时 30%，期末 70%
USUAL_WEIGHT = 0.3
FINAL_WEIGHT = 0.7

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "backup")


class BizError(Exception):
    """业务规则校验失败时抛出，路由层统一捕获并提示。"""


# 成绩记录的状态，对应实验二图7 状态图
ST_BLANK = "空白成绩"
ST_INPUT = "已录入"
ST_CALC = "已计算"
ST_SAVED = "已保存"
ST_PUBLISHED = "已发布"
ST_ARCHIVED = "已归档"

# 合法迁移：源状态 -> 允许到达的状态集合
STATUS_FLOW = {
    ST_BLANK: {ST_INPUT},
    ST_INPUT: {ST_CALC, ST_INPUT},
    ST_CALC: {ST_SAVED, ST_CALC},
    ST_SAVED: {ST_PUBLISHED, ST_SAVED},
    ST_PUBLISHED: {ST_ARCHIVED, ST_SAVED},
    ST_ARCHIVED: set(),
}


def check_status_flow(cur, target):
    """检查状态迁移是否合法，非法迁移直接拒绝，避免已归档成绩被改。"""
    if cur == target:
        return
    allowed = STATUS_FLOW.get(cur, set())
    if target not in allowed:
        raise BizError("成绩当前状态为 %s，不能直接变为 %s" % (cur, target))


# ---------------- 计算规则 ----------------
def calc_total(usual, final):
    """总评成绩 = 平时 × 30% + 期末 × 70%。"""
    return round(usual * USUAL_WEIGHT + final * FINAL_WEIGHT, 1)


def calc_gpa(total):
    """按分段换算绩点。"""
    if total >= 90:
        return 4.0
    if total >= 85:
        return 3.7
    if total >= 82:
        return 3.3
    if total >= 78:
        return 3.0
    if total >= 75:
        return 2.7
    if total >= 72:
        return 2.3
    if total >= 68:
        return 2.0
    if total >= 64:
        return 1.5
    if total >= 60:
        return 1.0
    return 0.0


def parse_score(value, label="成绩"):
    """把表单文本转成数值，非数字或空时给出中文提示。"""
    if value is None or str(value).strip() == "":
        raise BizError("%s不能为空" % label)
    try:
        return float(value)
    except (TypeError, ValueError):
        raise BizError("%s必须是数字，当前输入为 %s" % (label, value))


def check_score_range(usual, final):
    """成绩取值必须落在 0 到 100。"""
    for label, v in (("平时成绩", usual), ("期末成绩", final)):
        if v is None or v < 0 or v > 100:
            raise BizError("%s 应在 0 到 100 之间，当前值为 %s" % (label, v))


# ---------------- 学生档案 ----------------
def student_save(form, is_new):
    """新增或修改学生档案，同时维护家庭成员与职务信息。"""
    no = (form.get("student_no") or "").strip()
    name = (form.get("name") or "").strip()
    cls = (form.get("class_name") or "").strip()
    if not no:
        raise BizError("学号不能为空")
    if not name:
        raise BizError("姓名不能为空")
    if not cls:
        raise BizError("班级不能为空")

    data = {
        "student_no": no,
        "name": name,
        "sex": form.get("sex"),
        "birthday": form.get("birthday"),
        "class_name": cls,
        "enroll_total": _num(form.get("enroll_total")),
        "enroll_chinese": _num(form.get("enroll_chinese")),
        "enroll_math": _num(form.get("enroll_math")),
        "enroll_english": _num(form.get("enroll_english")),
        "phone": form.get("phone"),
    }
    check_enroll(data)
    if is_new:
        if dao.student_get(no):
            raise BizError("学号 %s 已存在" % no)
        dao.student_insert(data)
    else:
        if not dao.student_get(no):
            raise BizError("学号 %s 不存在" % no)
        dao.student_update(no, data)
    return no


def student_import(records):
    """批量导入学生档案，对应实验二图8 的扩展用例。

    返回成功条数与失败明细，失败的记录不影响成功的记录。
    """
    ok, errors = 0, []
    for i, rec in enumerate(records, start=1):
        try:
            student_save(rec, is_new=True)
            ok += 1
        except BizError as e:
            errors.append("第 %d 行 %s" % (i, str(e)))
    return ok, errors


def student_remove(student_no):
    """删除学生，级联删除其家庭、职务与成绩记录。"""
    if not dao.student_get(student_no):
        raise BizError("学号 %s 不存在" % student_no)
    dao.student_delete(student_no)


def _num(v, default=0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ---------------- 课程 ----------------
def course_save(form, is_new):
    no = (form.get("course_no") or "").strip()
    name = (form.get("course_name") or "").strip()
    if not no:
        raise BizError("课程号不能为空")
    if not name:
        raise BizError("课程名称不能为空")
    data = {
        "course_no": no,
        "course_name": name,
        "credit": _num(form.get("credit"), 2),
        "term": form.get("term"),
        "teacher_no": form.get("teacher_no") or None,
    }
    if is_new:
        if dao.course_get(no):
            raise BizError("课程号 %s 已存在" % no)
        dao.course_insert(data)
    else:
        if not dao.course_get(no):
            raise BizError("课程号 %s 不存在" % no)
        dao.course_update(no, data)


def check_enroll(data):
    """入学成绩必须落在合理区间，总分 0 到 750，单科 0 到 150。"""
    if data["enroll_total"] < 0 or data["enroll_total"] > 750:
        raise BizError("入学总分应在 0 到 750 之间，当前值为 %s" % data["enroll_total"])
    for key, label in (("enroll_chinese", "语文"), ("enroll_math", "数学"),
                       ("enroll_english", "英语")):
        v = data[key]
        if v < 0 or v > 150:
            raise BizError("%s成绩应在 0 到 150 之间，当前值为 %s" % (label, v))


def teacher_remove(teacher_no):
    """删除教师前检查是否还有课程引用。"""
    if not dao.teacher_get(teacher_no):
        raise BizError("工号 %s 不存在" % teacher_no)
    used = [c for c in dao.course_list() if c.get("teacher_no") == teacher_no]
    if used:
        names = "、".join(c["course_no"] for c in used)
        raise BizError("教师 %s 还承担课程 %s，请先调整课程后再删除" % (teacher_no, names))
    dao.teacher_delete(teacher_no)


def course_remove(course_no):
    """删除课程前先确认该课程没有成绩记录。"""
    rows = dao.score_list(course_no=course_no)
    if rows:
        raise BizError("课程 %s 已有 %d 条成绩记录，请先清空成绩" % (course_no, len(rows)))
    dao.course_delete(course_no)


# ---------------- 成绩管理 15 项操作 ----------------
def score_init(course_no, class_name, operator):
    """成绩册初始化：为指定班级的全体学生按课程建空白成绩记录。"""
    course = dao.course_get(course_no)
    if not course:
        raise BizError("课程 %s 不存在" % course_no)
    students = dao.student_list(class_name=class_name)
    if not students:
        raise BizError("班级 %s 没有学生记录" % class_name)

    created = 0
    for st in students:
        if dao.score_get(st["student_no"], course_no):
            continue
        dao.score_insert({
            "student_no": st["student_no"],
            "course_no": course_no,
            "usual_score": 0,
            "final_score": 0,
            "total_score": 0,
            "gpa": 0,
            "input_by": operator,
        })
        created += 1
    return created


def score_input(student_no, course_no, usual, final, operator, allow_update=True):
    """成绩录入。校验学号、课程、取值与重复，再计算总评与绩点并保存。"""
    if not dao.student_get(student_no):
        raise BizError("学号 %s 不存在" % student_no)
    if not dao.course_get(course_no):
        raise BizError("课程号 %s 不存在" % course_no)

    check_score_range(usual, final)

    exists = dao.score_get(student_no, course_no)
    if exists and not allow_update:
        raise BizError("该学生该课程已有成绩，请使用修改功能")

    total = calc_total(usual, final)
    gpa = calc_gpa(total)
    rec = {
        "student_no": student_no,
        "course_no": course_no,
        "usual_score": usual,
        "final_score": final,
        "total_score": total,
        "gpa": gpa,
        "input_by": operator,
    }
    if exists:
        cur = exists.get("status") or ST_INPUT
        check_status_flow(cur, ST_INPUT)
        dao.score_update(student_no, course_no, rec)
        dao.score_set_status(student_no, course_no, ST_INPUT)
        return "update"
    dao.score_insert(rec)
    dao.score_set_status(student_no, course_no, ST_INPUT)
    return "insert"


def score_transit(student_no, course_no, target):
    """成绩状态迁移，供发布、归档等操作调用。"""
    rec = dao.score_get(student_no, course_no)
    if not rec:
        raise BizError("该成绩记录不存在")
    cur = rec.get("status") or ST_INPUT
    check_status_flow(cur, target)
    dao.score_set_status(student_no, course_no, target)
    return cur, target


def score_publish(course_no):
    """发布成绩：把某课程已计算或已保存的成绩置为已发布。"""
    rows = dao.score_list(course_no=course_no)
    n = 0
    for r in rows:
        cur = r.get("status") or ST_INPUT
        if cur in (ST_CALC, ST_SAVED):
            dao.score_set_status(r["student_no"], course_no, ST_PUBLISHED)
            n += 1
    if n == 0:
        raise BizError("没有可发布的成绩，请先计算并保存")
    return n


def score_archive(course_no):
    """归档成绩：把已发布的成绩置为已归档。"""
    rows = dao.score_list(course_no=course_no)
    n = 0
    for r in rows:
        if (r.get("status") or "") == ST_PUBLISHED:
            dao.score_set_status(r["student_no"], course_no, ST_ARCHIVED)
            n += 1
    if n == 0:
        raise BizError("没有已发布的成绩可归档")
    return n


def score_delete_one(student_no, course_no):
    """删除单条成绩。"""
    if not dao.score_get(student_no, course_no):
        raise BizError("该成绩记录不存在")
    dao.score_delete(student_no, course_no)


def score_update_fields(student_no, course_no, usual, final, operator):
    """修改成绩，重新计算总评与绩点。"""
    if not dao.score_get(student_no, course_no):
        raise BizError("该成绩记录不存在")
    return score_input(student_no, course_no, usual, final, operator, allow_update=True)


def score_insert_row(student_no, course_no, usual, final, operator):
    """插入一条新成绩，若已存在则报错。"""
    if dao.score_get(student_no, course_no):
        raise BizError("该学生该课程成绩已存在，请使用追加或修改")
    return score_input(student_no, course_no, usual, final, operator, allow_update=False)


def score_append(records, operator):
    """追加：批量导入成绩，返回成功条数与失败明细。"""
    ok, errors = 0, []
    for i, rec in enumerate(records, start=1):
        try:
            score_input(rec["student_no"], rec["course_no"],
                        rec["usual"], rec["final"], operator)
            ok += 1
        except BizError as e:
            errors.append("第 %d 行 %s" % (i, str(e)))
        except (KeyError, ValueError):
            errors.append("第 %d 行格式不正确" % i)
    return ok, errors


def score_save_all(course_no):
    """保存：重新计算该课程全部记录的总评与绩点。"""
    rows = dao.score_list(course_no=course_no)
    n = 0
    for r in rows:
        total = calc_total(r["usual_score"], r["final_score"])
        gpa = calc_gpa(total)
        if total != r["total_score"] or gpa != r["gpa"]:
            dao.score_update(r["student_no"], course_no, {
                "usual_score": r["usual_score"],
                "final_score": r["final_score"],
                "total_score": total,
                "gpa": gpa,
                "input_by": r["input_by"],
            })
            n += 1
    # 计算完成后状态推进到已计算
    for r in rows:
        cur = r.get("status") or ST_INPUT
        if cur in (ST_INPUT, ST_BLANK):
            dao.score_set_status(r["student_no"], course_no, ST_CALC)
    return n


def score_calc(course_no):
    """计算：同保存，返回重算条数。"""
    return score_save_all(course_no)


def score_copy(src, dst):
    """拷贝：把源课程的成绩整门复制到目标课程。"""
    if not dao.course_get(src):
        raise BizError("源课程不存在")
    if not dao.course_get(dst):
        raise BizError("目标课程不存在")
    if src == dst:
        raise BizError("源课程与目标课程不能相同")
    return dao.score_copy_course(src, dst)


def score_sort(course_no):
    """排序：按总评成绩降序返回排名。"""
    return dao.score_rank(course_no)


def score_index(course_no):
    """索引：返回该课程成绩的索引清单，含学号、姓名与总评。"""
    rows = dao.score_list(course_no=course_no)
    rows.sort(key=lambda r: r["student_no"])
    return rows


def score_classify(course_no):
    """分类统计：按班级汇总与分数段分布。"""
    return {
        "by_class": dao.score_by_class(course_no),
        "distribution": dao.score_distribution(course_no),
    }


def score_read_in(course_no):
    """读入：重新从数据库载入某课程的成绩。"""
    return dao.score_list(course_no=course_no)


def score_clear(course_no):
    """清空某课程全部成绩。"""
    return dao.score_clear_course(course_no)


# ---------------- 用户与权限 ----------------
ROLES = ("管理员", "教师", "学生")


def user_login(user_name, password):
    u = dao.user_get(user_name)
    if not u:
        raise BizError("用户名或密码错误")
    if u["status"] != "normal":
        raise BizError("账号已被停用")
    if u["password"] != password:
        raise BizError("用户名或密码错误")
    return u


def user_add(form):
    name = (form.get("user_name") or "").strip()
    pwd = form.get("password") or ""
    role = form.get("role")
    if not name:
        raise BizError("用户名不能为空")
    if len(pwd) < 4:
        raise BizError("密码长度不能少于 4 位")
    if role not in ROLES:
        raise BizError("角色只能是管理员、教师或学生")
    if dao.user_get(name):
        raise BizError("用户名 %s 已存在" % name)
    dao.user_insert({
        "user_name": name,
        "password": pwd,
        "role": role,
        "related_no": form.get("related_no") or None,
    })


def user_remove(user_name, current_user):
    if user_name == current_user:
        raise BizError("不能删除当前登录的账号")
    if not dao.user_get(user_name):
        raise BizError("用户不存在")
    dao.user_delete(user_name)


def user_change_password(user_name, old_pwd, new_pwd):
    u = dao.user_get(user_name)
    if not u:
        raise BizError("用户不存在")
    if u["password"] != old_pwd:
        raise BizError("原密码不正确")
    if len(new_pwd) < 4:
        raise BizError("新密码长度不能少于 4 位")
    dao.user_update_password(user_name, new_pwd)


def can_manage_scores(role):
    return role in ("管理员", "教师")


def can_manage_users(role):
    return role == "管理员"


def can_manage_backup(role):
    return role == "管理员"


# ---------------- 备份与恢复 ----------------
def backup_now(operator):
    """备份：把数据库文件复制到 backup 目录，并写备份日志。"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    no = "BK" + stamp
    seq = 1
    while dao.backup_get(no):
        seq += 1
        no = "BK" + stamp + "_%02d" % seq
    fname = "grade_%s.db" % stamp
    dest = os.path.join(BACKUP_DIR, fname)
    src = dao.DB_PATH
    if not os.path.exists(src):
        raise BizError("数据库文件不存在，无法备份")
    shutil.copy2(src, dest)
    size = os.path.getsize(dest)
    dao.backup_insert({
        "backup_no": no,
        "backup_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file_name": fname,
        "file_size": size,
        "operator": operator,
        "result": "成功",
    })
    return no, fname, size


def restore(backup_no, operator):
    """恢复：用备份文件覆盖当前数据库。"""
    rec = dao.backup_get(backup_no)
    if not rec:
        raise BizError("备份记录不存在")
    src = os.path.join(BACKUP_DIR, rec["file_name"])
    if not os.path.exists(src):
        raise BizError("备份文件已丢失，无法恢复")
    shutil.copy2(src, dao.DB_PATH)
    dao.backup_insert({
        "backup_no": "RS" + datetime.now().strftime("%Y%m%d_%H%M%S"),
        "backup_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file_name": rec["file_name"],
        "file_size": rec["file_size"],
        "operator": operator,
        "result": "已恢复",
    })
    return rec["file_name"]
