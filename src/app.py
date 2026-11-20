# -*- coding: utf-8 -*-
"""学生成绩管理系统 主程序

表现层与路由层。对应实验二构件图中的表现层构件与主控模块，
按角色控制可访问的功能，所有业务规则交给 service 层处理。
"""
import csv
import io
import os
from functools import wraps

from flask import (Flask, Response, flash, redirect, render_template,
                   request, session, url_for)

import dao
import service

app = Flask(__name__)
app.secret_key = "grade-management-system-2025"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------- 登录与权限控制 ----------------
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("请先登录", "warn")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if session.get("role") not in roles:
                flash("当前角色无权访问该功能", "error")
                return redirect(url_for("index"))
            return view(*args, **kwargs)
        return wrapper
    return decorator


@app.context_processor
def inject_globals():
    return {
        "current_user": session.get("user"),
        "current_role": session.get("role"),
        "can_score": service.can_manage_scores(session.get("role", "")),
        "can_user": service.can_manage_users(session.get("role", "")),
        "can_backup": service.can_manage_backup(session.get("role", "")),
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            u = service.user_login(request.form.get("user_name", ""),
                                   request.form.get("password", ""))
            session["user"] = u["user_name"]
            session["role"] = u["role"]
            session["related_no"] = u["related_no"]
            flash("登录成功", "ok")
            return redirect(url_for("index"))
        except service.BizError as e:
            flash(str(e), "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("已退出登录", "ok")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    stats = {
        "students": len(dao.student_list()),
        "courses": len(dao.course_list()),
        "scores": len(dao.score_list()),
        "teachers": len(dao.teacher_list()),
    }
    return render_template("index.html", stats=stats)


# ---------------- 学生档案管理 P1 ----------------
@app.route("/students")
@login_required
def student_list():
    kw = request.args.get("kw", "")
    cls = request.args.get("cls", "")
    rows = dao.student_list(keyword=kw, class_name=cls)
    return render_template("student_list.html", rows=rows,
                           classes=dao.class_list(), kw=kw, cls=cls)


@app.route("/students/new", methods=["GET", "POST"])
@login_required
@role_required("管理员")
def student_new():
    if request.method == "POST":
        try:
            no = service.student_save(request.form, is_new=True)
            flash("学生 %s 录入成功" % no, "ok")
            return redirect(url_for("student_detail", student_no=no))
        except service.BizError as e:
            flash(str(e), "error")
    return render_template("student_form.html", row=None, is_new=True)


@app.route("/students/<student_no>")
@login_required
def student_detail(student_no):
    row = dao.student_get(student_no)
    if not row:
        flash("学生不存在", "error")
        return redirect(url_for("student_list"))
    return render_template("student_detail.html", row=row,
                           family=dao.family_list(student_no),
                           duties=dao.duty_list(student_no))


@app.route("/students/<student_no>/edit", methods=["GET", "POST"])
@login_required
@role_required("管理员")
def student_edit(student_no):
    row = dao.student_get(student_no)
    if not row:
        flash("学生不存在", "error")
        return redirect(url_for("student_list"))
    if request.method == "POST":
        try:
            service.student_save(request.form, is_new=False)
            flash("学生信息已更新", "ok")
            return redirect(url_for("student_detail", student_no=student_no))
        except service.BizError as e:
            flash(str(e), "error")
    return render_template("student_form.html", row=row, is_new=False)


@app.route("/students/<student_no>/delete", methods=["POST"])
@login_required
@role_required("管理员")
def student_delete(student_no):
    try:
        service.student_remove(student_no)
        flash("学生 %s 已删除" % student_no, "ok")
    except service.BizError as e:
        flash(str(e), "error")
    return redirect(url_for("student_list"))


@app.route("/students/import", methods=["POST"])
@login_required
@role_required("管理员")
def student_import():
    """批量导入学生档案，对应实验二图8 的扩展用例。"""
    text = request.form.get("batch", "")
    records = []
    for line in text.strip().splitlines():
        parts = [p.strip() for p in line.replace("，", ",").split(",")]
        if len(parts) < 5:
            continue
        records.append({
            "student_no": parts[0], "name": parts[1], "sex": parts[2],
            "birthday": parts[3], "class_name": parts[4],
            "enroll_total": parts[5] if len(parts) > 5 else 0,
            "enroll_chinese": parts[6] if len(parts) > 6 else 0,
            "enroll_math": parts[7] if len(parts) > 7 else 0,
            "enroll_english": parts[8] if len(parts) > 8 else 0,
            "phone": parts[9] if len(parts) > 9 else "",
        })
    ok, errors = service.student_import(records)
    flash("批量导入完成，成功 %d 条，失败 %d 条" % (ok, len(errors)),
          "ok" if not errors else "warn")
    for e in errors[:5]:
        flash(e, "error")
    return redirect(url_for("student_list"))


@app.route("/students/<student_no>/print")
@login_required
def student_print(student_no):
    """打印学生档案表，对应实验二图8 的扩展用例。"""
    row = dao.student_get(student_no)
    if not row:
        flash("学生不存在", "error")
        return redirect(url_for("student_list"))
    return render_template("student_print.html", row=row,
                           family=dao.family_list(student_no),
                           duties=dao.duty_list(student_no))


@app.route("/students/<student_no>/family", methods=["POST"])
@login_required
@role_required("管理员")
def family_add(student_no):
    try:
        if not request.form.get("member_name"):
            raise service.BizError("成员姓名不能为空")
        dao.family_insert(student_no, request.form)
        flash("家庭成员已添加", "ok")
    except service.BizError as e:
        flash(str(e), "error")
    return redirect(url_for("student_detail", student_no=student_no))


@app.route("/family/<int:fid>/delete", methods=["POST"])
@login_required
@role_required("管理员")
def family_delete(fid):
    sn = request.form.get("student_no")
    dao.family_delete(fid)
    flash("家庭成员已删除", "ok")
    return redirect(url_for("student_detail", student_no=sn))


@app.route("/students/<student_no>/duty", methods=["POST"])
@login_required
@role_required("管理员")
def duty_add(student_no):
    try:
        if not request.form.get("duty_name"):
            raise service.BizError("职务名称不能为空")
        dao.duty_insert(student_no, request.form)
        flash("职务信息已添加", "ok")
    except service.BizError as e:
        flash(str(e), "error")
    return redirect(url_for("student_detail", student_no=student_no))


@app.route("/duty/<int:did>/delete", methods=["POST"])
@login_required
@role_required("管理员")
def duty_delete(did):
    sn = request.form.get("student_no")
    dao.duty_delete(did)
    flash("职务信息已删除", "ok")
    return redirect(url_for("student_detail", student_no=sn))


# ---------------- 课程与教师 ----------------
@app.route("/courses")
@login_required
def course_list():
    return render_template("course_list.html", rows=dao.course_list())


@app.route("/courses/new", methods=["GET", "POST"])
@login_required
@role_required("管理员")
def course_new():
    if request.method == "POST":
        try:
            service.course_save(request.form, is_new=True)
            flash("课程已添加", "ok")
            return redirect(url_for("course_list"))
        except service.BizError as e:
            flash(str(e), "error")
    return render_template("course_form.html", row=None,
                           teachers=dao.teacher_list(), is_new=True)


@app.route("/courses/<course_no>/edit", methods=["GET", "POST"])
@login_required
@role_required("管理员")
def course_edit(course_no):
    row = dao.course_get(course_no)
    if not row:
        flash("课程不存在", "error")
        return redirect(url_for("course_list"))
    if request.method == "POST":
        try:
            service.course_save(request.form, is_new=False)
            flash("课程已更新", "ok")
            return redirect(url_for("course_list"))
        except service.BizError as e:
            flash(str(e), "error")
    return render_template("course_form.html", row=row,
                           teachers=dao.teacher_list(), is_new=False)


@app.route("/courses/<course_no>/delete", methods=["POST"])
@login_required
@role_required("管理员")
def course_delete(course_no):
    try:
        service.course_remove(course_no)
        flash("课程已删除", "ok")
    except service.BizError as e:
        flash(str(e), "error")
    return redirect(url_for("course_list"))


@app.route("/teachers", methods=["GET", "POST"])
@login_required
@role_required("管理员")
def teacher_list():
    if request.method == "POST":
        try:
            if not request.form.get("teacher_no") or not request.form.get("name"):
                raise service.BizError("工号与姓名不能为空")
            if dao.teacher_get(request.form["teacher_no"]):
                raise service.BizError("工号已存在")
            dao.teacher_insert(request.form)
            flash("教师已添加", "ok")
        except service.BizError as e:
            flash(str(e), "error")
        return redirect(url_for("teacher_list"))
    return render_template("teacher_list.html", rows=dao.teacher_list())


@app.route("/teachers/<teacher_no>/delete", methods=["POST"])
@login_required
@role_required("管理员")
def teacher_delete(teacher_no):
    try:
        service.teacher_remove(teacher_no)
        flash("教师已删除", "ok")
    except service.BizError as e:
        flash(str(e), "error")
    return redirect(url_for("teacher_list"))


# ---------------- 成绩管理 P2 ----------------
@app.route("/scores")
@login_required
@role_required("管理员", "教师")
def score_list():
    course_no = request.args.get("course", "")
    cls = request.args.get("cls", "")
    kw = request.args.get("kw", "")
    rows = dao.score_list(course_no=course_no, class_name=cls, keyword=kw)
    return render_template("score_list.html", rows=rows,
                           courses=dao.course_list(), classes=dao.class_list(),
                           course_no=course_no, cls=cls, kw=kw)


@app.route("/scores/init", methods=["POST"])
@login_required
@role_required("管理员", "教师")
def score_init():
    try:
        n = service.score_init(request.form.get("course_no", ""),
                               request.form.get("class_name", ""),
                               session["user"])
        flash("成绩册初始化完成，新建 %d 条记录" % n, "ok")
    except service.BizError as e:
        flash(str(e), "error")
    return redirect(url_for("score_list", course=request.form.get("course_no", "")))


@app.route("/scores/input", methods=["POST"])
@login_required
@role_required("管理员", "教师")
def score_input():
    course = request.form.get("course_no", "")
    try:
        usual = service.parse_score(request.form.get("usual"), "平时成绩")
        final = service.parse_score(request.form.get("final"), "期末成绩")
        action = service.score_input(
            request.form.get("student_no", "").strip(),
            course, usual, final, session["user"])
        flash("成绩已保存" if action == "insert" else "成绩已更新", "ok")
    except service.BizError as e:
        flash(str(e), "error")
    return redirect(url_for("score_list", course=course))


@app.route("/scores/<student_no>/<course_no>/delete", methods=["POST"])
@login_required
@role_required("管理员", "教师")
def score_delete_one(student_no, course_no):
    try:
        service.score_delete_one(student_no, course_no)
        flash("成绩已删除", "ok")
    except service.BizError as e:
        flash(str(e), "error")
    return redirect(url_for("score_list", course=course_no))


@app.route("/scores/append", methods=["POST"])
@login_required
@role_required("管理员", "教师")
def score_append():
    """追加：按粘贴的文本批量导入成绩，每行格式为 学号,课程号,平时,期末。"""
    text = request.form.get("batch", "")
    records = []
    for line in text.strip().splitlines():
        parts = [p.strip() for p in line.replace("，", ",").split(",")]
        if len(parts) < 4:
            continue
        records.append({
            "student_no": parts[0], "course_no": parts[1],
            "usual": float(parts[2]), "final": float(parts[3]),
        })
    ok, errors = service.score_append(records, session["user"])
    flash("追加完成，成功 %d 条，失败 %d 条" % (ok, len(errors)), "ok" if not errors else "warn")
    for e in errors[:5]:
        flash(e, "error")
    return redirect(url_for("score_list"))


@app.route("/scores/ops/<op>", methods=["POST"])
@login_required
@role_required("管理员", "教师")
def score_ops(op):
    """成绩管理的计算、保存、拷贝、排序、索引、分类统计、读入、清空。"""
    course = request.form.get("course_no", "")
    try:
        if op == "calc":
            n = service.score_calc(course)
            flash("已重算 %d 条记录的总评与绩点" % n, "ok")
        elif op == "save":
            n = service.score_save_all(course)
            flash("已保存，更新 %d 条记录" % n, "ok")
        elif op == "copy":
            n = service.score_copy(course, request.form.get("dst_course", ""))
            flash("已拷贝 %d 条成绩记录" % n, "ok")
        elif op == "sort":
            rows = service.score_sort(course)
            return render_template("score_rank.html", rows=rows,
                                   course=dao.course_get(course))
        elif op == "index":
            rows = service.score_index(course)
            return render_template("score_index.html", rows=rows,
                                   course=dao.course_get(course))
        elif op == "classify":
            data = service.score_classify(course)
            return render_template("score_classify.html", data=data,
                                   course=dao.course_get(course))
        elif op == "read":
            rows = service.score_read_in(course)
            flash("已从数据库读入 %d 条成绩" % len(rows), "ok")
        elif op == "clear":
            n = service.score_clear(course)
            flash("已清空 %d 条成绩" % n, "ok")
        else:
            flash("不支持的操作", "error")
    except service.BizError as e:
        flash(str(e), "error")
    return redirect(url_for("score_list", course=course))


@app.route("/scores/export/<course_no>")
@login_required
def score_export(course_no):
    """导出某课程成绩为 CSV 文件，对应实验二图9 的扩展用例。"""
    course = dao.course_get(course_no)
    if not course:
        flash("课程不存在", "error")
        return redirect(url_for("score_report"))
    rows = dao.score_list(course_no=course_no)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["学号", "姓名", "班级", "课程号", "课程名称",
                     "平时", "期末", "总评", "绩点", "状态"])
    for r in rows:
        writer.writerow([r["student_no"], r["student_name"], r["class_name"],
                         r["course_no"], r["course_name"], r["usual_score"],
                         r["final_score"], r["total_score"], r["gpa"],
                         r.get("status") or ""])
    data = buf.getvalue().encode("utf-8-sig")
    return Response(data, mimetype="text/csv",
                    headers={"Content-Disposition":
                             "attachment; filename=score_%s.csv" % course_no})


@app.route("/scores/ops2/<op>", methods=["POST"])
@login_required
@role_required("管理员", "教师")
def score_status_ops(op):
    """成绩状态操作：发布、归档，对应实验二图7 状态图。"""
    course = request.form.get("course_no", "")
    try:
        if op == "publish":
            n = service.score_publish(course)
            flash("已发布 %d 条成绩" % n, "ok")
        elif op == "archive":
            n = service.score_archive(course)
            flash("已归档 %d 条成绩" % n, "ok")
        else:
            flash("不支持的操作", "error")
    except service.BizError as e:
        flash(str(e), "error")
    return redirect(url_for("score_list", course=course))


@app.route("/scores/report")
@login_required
def score_report():
    """综合查询与统计 P3：按课程汇总与按班级汇总。"""
    return render_template("score_report.html",
                           by_course=dao.score_by_course(),
                           courses=dao.course_list())


@app.route("/scores/report/<course_no>")
@login_required
def score_report_course(course_no):
    course = dao.course_get(course_no)
    if not course:
        flash("课程不存在", "error")
        return redirect(url_for("score_report"))
    return render_template("score_report_detail.html",
                           course=course,
                           by_class=dao.score_by_class(course_no),
                           dist=dao.score_distribution(course_no),
                           rows=dao.score_list(course_no=course_no))


@app.route("/my-score")
@login_required
def my_score():
    """学生查询个人成绩。"""
    no = session.get("related_no")
    if not no:
        flash("当前账号未关联学号", "error")
        return redirect(url_for("index"))
    rows, credit, avg_gpa = dao.score_student_summary(no)
    return render_template("my_score.html", rows=rows, credit=credit,
                           avg_gpa=avg_gpa, student=dao.student_get(no))


# ---------------- 用户与权限管理 P4 ----------------
@app.route("/users")
@login_required
@role_required("管理员")
def user_list():
    return render_template("user_list.html", rows=dao.user_list())


@app.route("/users/new", methods=["POST"])
@login_required
@role_required("管理员")
def user_new():
    try:
        service.user_add(request.form)
        flash("用户已添加", "ok")
    except service.BizError as e:
        flash(str(e), "error")
    return redirect(url_for("user_list"))


@app.route("/users/<user_name>/delete", methods=["POST"])
@login_required
@role_required("管理员")
def user_delete(user_name):
    try:
        service.user_remove(user_name, session["user"])
        flash("用户已删除", "ok")
    except service.BizError as e:
        flash(str(e), "error")
    return redirect(url_for("user_list"))


@app.route("/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        try:
            service.user_change_password(session["user"],
                                         request.form.get("old", ""),
                                         request.form.get("new", ""))
            flash("密码修改成功", "ok")
            return redirect(url_for("index"))
        except service.BizError as e:
            flash(str(e), "error")
    return render_template("password.html")


# ---------------- 数据备份与恢复 P5 ----------------
@app.route("/backup")
@login_required
@role_required("管理员")
def backup_list():
    return render_template("backup_list.html", rows=dao.backup_list())


@app.route("/backup/now", methods=["POST"])
@login_required
@role_required("管理员")
def backup_now():
    try:
        no, fname, size = service.backup_now(session["user"])
        flash("备份完成，编号 %s，文件 %s，大小 %d 字节" % (no, fname, size), "ok")
    except service.BizError as e:
        flash(str(e), "error")
    return redirect(url_for("backup_list"))


@app.route("/backup/<backup_no>/restore", methods=["POST"])
@login_required
@role_required("管理员")
def backup_restore(backup_no):
    try:
        fname = service.restore(backup_no, session["user"])
        flash("已从 %s 恢复数据" % fname, "ok")
    except service.BizError as e:
        flash(str(e), "error")
    return redirect(url_for("backup_list"))


if __name__ == "__main__":
    if not os.path.exists(dao.DB_PATH):
        dao.init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)
