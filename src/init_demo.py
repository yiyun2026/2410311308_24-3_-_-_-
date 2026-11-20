# -*- coding: utf-8 -*-
"""初始化演示数据

建表后写入演示用的学生、课程、教师、用户与成绩记录，
便于打开系统后立即看到完整效果。
"""
import os
import random

import dao
import service

STUDENTS = [
    ("2410311301", "陈思远", "男", "2006-03-12", "24计科1", 612, 118, 132, 121, "13800000101"),
    ("2410311302", "李雅雯", "女", "2006-07-25", "24计科1", 628, 126, 138, 129, "13800000102"),
    ("2410311303", "王浩然", "男", "2006-01-09", "24计科1", 596, 112, 128, 118, "13800000103"),
    ("2410311304", "张诗涵", "女", "2006-11-30", "24计科1", 641, 131, 140, 133, "13800000104"),
    ("2410311305", "刘子墨", "男", "2006-05-18", "24计科1", 583, 108, 126, 115, "13800000105"),
    ("2410311306", "赵梦琪", "女", "2006-09-22", "24计科2", 655, 134, 145, 138, "13800000106"),
    ("2410311307", "孙嘉豪", "男", "2006-02-14", "24计科2", 604, 115, 130, 122, "13800000107"),
    ("2410311308", "龚治榕", "男", "2006-06-08", "24计科3", 637, 128, 142, 131, "13800000108"),
    ("2410311309", "周雨桐", "女", "2006-12-03", "24计科3", 571, 106, 121, 112, "13800000109"),
    ("2410311310", "吴俊杰", "男", "2006-04-27", "24计科3", 619, 120, 135, 125, "13800000110"),
]

TEACHERS = [
    ("T001", "赵岚", "教授"),
    ("T002", "何海江", "副教授"),
    ("T003", "程努华", "讲师"),
]

COURSES = [
    ("CS101", "程序设计基础", 4, "2025-2026-1", "T001"),
    ("CS102", "数据结构", 4, "2025-2026-1", "T002"),
    ("CS103", "数据库原理", 3, "2025-2026-1", "T003"),
    ("CS104", "软件工程", 3, "2025-2026-2", "T001"),
]

FAMILY = [
    ("陈思远", [("陈建国", "父", "市第一中学", "13900000101"), ("刘敏", "母", "市财政局", "13900000102")]),
    ("李雅雯", [("李国强", "父", "县人民医院", "13900000103"), ("王丽", "母", "县实验小学", "13900000104")]),
    ("龚治榕", [("龚志明", "父", "市供电公司", "13900000105"), ("周芳", "母", "市第三医院", "13900000106")]),
]

DUTIES = [
    ("2410311301", "班长", "2024-09-01", "负责班级日常事务"),
    ("2410311302", "学习委员", "2024-09-01", "负责作业收交"),
    ("2410311308", "课代表", "2024-09-15", "程序设计基础课代表"),
    ("2410311306", "团支部书记", "2024-09-01", ""),
]

USERS = [
    ("admin", "123456", "管理员", None),
    ("teacher01", "123456", "教师", "T001"),
    ("teacher02", "123456", "教师", "T002"),
    ("2410311308", "123456", "学生", "2410311308"),
    ("2410311301", "123456", "学生", "2410311301"),
]


def rand_score(base, spread=18):
    v = base + random.randint(-spread, spread)
    return max(35, min(99, v))


def main():
    if os.path.exists(dao.DB_PATH):
        os.remove(dao.DB_PATH)
    dao.init_db()

    for s in STUDENTS:
        dao.student_insert({
            "student_no": s[0], "name": s[1], "sex": s[2], "birthday": s[3],
            "class_name": s[4], "enroll_total": s[5], "enroll_chinese": s[6],
            "enroll_math": s[7], "enroll_english": s[8], "phone": s[9],
        })

    for t in TEACHERS:
        dao.teacher_insert({"teacher_no": t[0], "name": t[1], "title": t[2]})

    for c in COURSES:
        dao.course_insert({
            "course_no": c[0], "course_name": c[1], "credit": c[2],
            "term": c[3], "teacher_no": c[4],
        })

    for name, members in FAMILY:
        stu = dao.query_one("SELECT student_no FROM student WHERE name = ?", (name,))
        if not stu:
            continue
        for m in members:
            dao.family_insert(stu["student_no"], {
                "member_name": m[0], "relation": m[1],
                "work_unit": m[2], "phone": m[3],
            })

    for d in DUTIES:
        dao.duty_insert(d[0], {"duty_name": d[1], "start_date": d[2], "remark": d[3]})

    for u in USERS:
        dao.user_insert({
            "user_name": u[0], "password": u[1], "role": u[2], "related_no": u[3],
        })

    # 为每门课程生成成绩
    random.seed(20251113)
    for c in COURSES:
        for s in STUDENTS:
            usual = rand_score(82)
            final = rand_score(80)
            try:
                service.score_input(s[0], c[0], usual, final, "teacher01")
            except service.BizError:
                pass

    # 系统初始化后立刻做一次备份，便于演示恢复功能
    try:
        service.backup_now("admin")
    except service.BizError:
        pass

    print("演示数据初始化完成")
    print("学生 %d 名，课程 %d 门，成绩 %d 条" % (
        len(dao.student_list()), len(dao.course_list()), len(dao.score_list())))
    print("账号 admin / 123456，teacher01 / 123456，2410311308 / 123456")


if __name__ == "__main__":
    main()
