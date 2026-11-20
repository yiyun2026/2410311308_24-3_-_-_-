# -*- coding: utf-8 -*-
"""数据访问层

封装对 SQLite 的全部读写操作。业务层只调用本模块的函数，
不直接书写 SQL，便于后续替换为 MySQL 或其他数据库。
对应实验二构件图中的数据访问层构件。
"""
import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "grade.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def get_conn():
    """取得数据库连接，行结果可按列名访问。"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """按 schema.sql 重建全部数据表。"""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        script = f.read()
    conn = get_conn()
    try:
        conn.executescript(script)
        conn.commit()
    finally:
        conn.close()


def query_all(sql, params=()):
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def query_one(sql, params=()):
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def execute(sql, params=()):
    """执行单条写操作，返回受影响行数。"""
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def execute_many(sql, seq):
    conn = get_conn()
    try:
        cur = conn.executemany(sql, seq)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------- D1 学生 ----------------
def student_list(keyword="", class_name=""):
    sql = "SELECT * FROM student WHERE 1=1"
    params = []
    if keyword:
        sql += " AND (student_no LIKE ? OR name LIKE ?)"
        params += ["%" + keyword + "%", "%" + keyword + "%"]
    if class_name:
        sql += " AND class_name = ?"
        params.append(class_name)
    sql += " ORDER BY student_no"
    return query_all(sql, params)


def student_get(student_no):
    return query_one("SELECT * FROM student WHERE student_no = ?", (student_no,))


def student_insert(data):
    return execute(
        """INSERT INTO student
           (student_no, name, sex, birthday, class_name,
            enroll_total, enroll_chinese, enroll_math, enroll_english, phone, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (data["student_no"], data["name"], data.get("sex"), data.get("birthday"),
         data["class_name"], data.get("enroll_total", 0), data.get("enroll_chinese", 0),
         data.get("enroll_math", 0), data.get("enroll_english", 0),
         data.get("phone"), now_str()),
    )


def student_update(student_no, data):
    return execute(
        """UPDATE student SET name=?, sex=?, birthday=?, class_name=?,
           enroll_total=?, enroll_chinese=?, enroll_math=?, enroll_english=?, phone=?
           WHERE student_no=?""",
        (data["name"], data.get("sex"), data.get("birthday"), data["class_name"],
         data.get("enroll_total", 0), data.get("enroll_chinese", 0),
         data.get("enroll_math", 0), data.get("enroll_english", 0),
         data.get("phone"), student_no),
    )


def student_delete(student_no):
    return execute("DELETE FROM student WHERE student_no = ?", (student_no,))


def class_list():
    return [r["class_name"] for r in
            query_all("SELECT DISTINCT class_name FROM student ORDER BY class_name")]


# ---------------- D2 家庭成员 ----------------
def family_list(student_no):
    return query_all(
        "SELECT * FROM family_member WHERE student_no = ? ORDER BY id", (student_no,))


def family_insert(student_no, data):
    return execute(
        """INSERT INTO family_member (student_no, member_name, relation, work_unit, phone)
           VALUES (?,?,?,?,?)""",
        (student_no, data["member_name"], data.get("relation"),
         data.get("work_unit"), data.get("phone")),
    )


def family_delete(fid):
    return execute("DELETE FROM family_member WHERE id = ?", (fid,))


# ---------------- D3 职务信息 ----------------
def duty_list(student_no):
    return query_all("SELECT * FROM duty WHERE student_no = ? ORDER BY id", (student_no,))


def duty_insert(student_no, data):
    return execute(
        "INSERT INTO duty (student_no, duty_name, start_date, remark) VALUES (?,?,?,?)",
        (student_no, data["duty_name"], data.get("start_date"), data.get("remark")),
    )


def duty_delete(did):
    return execute("DELETE FROM duty WHERE id = ?", (did,))


# ---------------- 教师 ----------------
def teacher_list():
    return query_all("SELECT * FROM teacher ORDER BY teacher_no")


def teacher_get(teacher_no):
    return query_one("SELECT * FROM teacher WHERE teacher_no = ?", (teacher_no,))


def teacher_insert(data):
    return execute(
        "INSERT INTO teacher (teacher_no, name, title) VALUES (?,?,?)",
        (data["teacher_no"], data["name"], data.get("title")),
    )


def teacher_update(teacher_no, data):
    return execute(
        "UPDATE teacher SET name=?, title=? WHERE teacher_no=?",
        (data["name"], data.get("title"), teacher_no),
    )


def teacher_delete(teacher_no):
    return execute("DELETE FROM teacher WHERE teacher_no = ?", (teacher_no,))


# ---------------- D4 课程 ----------------
def course_list(term=""):
    sql = """SELECT c.*, t.name AS teacher_name FROM course c
             LEFT JOIN teacher t ON c.teacher_no = t.teacher_no"""
    params = []
    if term:
        sql += " WHERE c.term = ?"
        params.append(term)
    sql += " ORDER BY c.course_no"
    return query_all(sql, params)


def course_get(course_no):
    return query_one("SELECT * FROM course WHERE course_no = ?", (course_no,))


def course_insert(data):
    return execute(
        """INSERT INTO course (course_no, course_name, credit, term, teacher_no)
           VALUES (?,?,?,?,?)""",
        (data["course_no"], data["course_name"], data.get("credit", 2),
         data.get("term"), data.get("teacher_no")),
    )


def course_update(course_no, data):
    return execute(
        "UPDATE course SET course_name=?, credit=?, term=?, teacher_no=? WHERE course_no=?",
        (data["course_name"], data.get("credit", 2), data.get("term"),
         data.get("teacher_no"), course_no),
    )


def course_delete(course_no):
    return execute("DELETE FROM course WHERE course_no = ?", (course_no,))


def term_list():
    return [r["term"] for r in
            query_all("SELECT DISTINCT term FROM course WHERE term IS NOT NULL ORDER BY term")]


# ---------------- D5 成绩 ----------------
def score_list(course_no="", class_name="", keyword="", student_no=""):
    sql = """SELECT s.*, st.name AS student_name, st.class_name,
                    c.course_name, c.credit
             FROM score s
             JOIN student st ON s.student_no = st.student_no
             JOIN course c ON s.course_no = c.course_no
             WHERE 1=1"""
    params = []
    if course_no:
        sql += " AND s.course_no = ?"
        params.append(course_no)
    if class_name:
        sql += " AND st.class_name = ?"
        params.append(class_name)
    if keyword:
        sql += " AND (st.student_no LIKE ? OR st.name LIKE ?)"
        params += ["%" + keyword + "%", "%" + keyword + "%"]
    if student_no:
        sql += " AND s.student_no = ?"
        params.append(student_no)
    sql += " ORDER BY s.course_no, st.student_no"
    return query_all(sql, params)


def score_get(student_no, course_no):
    return query_one(
        "SELECT * FROM score WHERE student_no = ? AND course_no = ?",
        (student_no, course_no))


def score_insert(rec):
    return execute(
        """INSERT INTO score
           (student_no, course_no, usual_score, final_score, total_score, gpa, input_by, input_time)
           VALUES (?,?,?,?,?,?,?,?)""",
        (rec["student_no"], rec["course_no"], rec["usual_score"], rec["final_score"],
         rec["total_score"], rec["gpa"], rec.get("input_by"), now_str()),
    )


def score_update(student_no, course_no, rec):
    return execute(
        """UPDATE score SET usual_score=?, final_score=?, total_score=?, gpa=?,
           input_by=?, input_time=? WHERE student_no=? AND course_no=?""",
        (rec["usual_score"], rec["final_score"], rec["total_score"], rec["gpa"],
         rec.get("input_by"), now_str(), student_no, course_no),
    )


def score_delete(student_no, course_no):
    return execute(
        "DELETE FROM score WHERE student_no = ? AND course_no = ?",
        (student_no, course_no))


def score_set_status(student_no, course_no, status):
    """更新成绩记录的状态，对应状态图中的状态迁移。"""
    return execute(
        "UPDATE score SET status = ? WHERE student_no = ? AND course_no = ?",
        (status, student_no, course_no))


def score_count_by_status(course_no=""):
    """按状态统计成绩记录条数。"""
    sql = "SELECT status, COUNT(*) AS cnt FROM score WHERE 1=1"
    params = []
    if course_no:
        sql += " AND course_no = ?"
        params.append(course_no)
    sql += " GROUP BY status"
    return query_all(sql, params)


def score_clear_course(course_no):
    return execute("DELETE FROM score WHERE course_no = ?", (course_no,))


def score_copy_course(src_course_no, dst_course_no):
    """把一门课的全部成绩拷贝到另一门课。"""
    rows = query_all("SELECT * FROM score WHERE course_no = ?", (src_course_no,))
    seq = [(r["student_no"], dst_course_no, r["usual_score"], r["final_score"],
            r["total_score"], r["gpa"], r["input_by"], now_str()) for r in rows]
    if not seq:
        return 0
    return execute_many(
        """INSERT OR REPLACE INTO score
           (student_no, course_no, usual_score, final_score, total_score, gpa, input_by, input_time)
           VALUES (?,?,?,?,?,?,?,?)""", seq)


def score_by_class(course_no):
    """按班级汇总某门课的成绩，用于分类统计。"""
    return query_all(
        """SELECT st.class_name,
                  COUNT(*) AS cnt,
                  ROUND(AVG(s.total_score), 2) AS avg_score,
                  MAX(s.total_score) AS max_score,
                  MIN(s.total_score) AS min_score,
                  SUM(CASE WHEN s.total_score >= 60 THEN 1 ELSE 0 END) AS pass_cnt
           FROM score s JOIN student st ON s.student_no = st.student_no
           WHERE s.course_no = ?
           GROUP BY st.class_name ORDER BY st.class_name""", (course_no,))


def score_by_course():
    """按课程汇总，用于分类统计。"""
    return query_all(
        """SELECT c.course_no, c.course_name,
                  COUNT(s.id) AS cnt,
                  ROUND(AVG(s.total_score), 2) AS avg_score,
                  MAX(s.total_score) AS max_score,
                  MIN(s.total_score) AS min_score,
                  SUM(CASE WHEN s.total_score >= 60 THEN 1 ELSE 0 END) AS pass_cnt
           FROM course c LEFT JOIN score s ON c.course_no = s.course_no
           GROUP BY c.course_no ORDER BY c.course_no""")


def score_distribution(course_no):
    """成绩分段分布。"""
    return query_one(
        """SELECT
             SUM(CASE WHEN total_score >= 90 THEN 1 ELSE 0 END) AS seg90,
             SUM(CASE WHEN total_score >= 80 AND total_score < 90 THEN 1 ELSE 0 END) AS seg80,
             SUM(CASE WHEN total_score >= 70 AND total_score < 80 THEN 1 ELSE 0 END) AS seg70,
             SUM(CASE WHEN total_score >= 60 AND total_score < 70 THEN 1 ELSE 0 END) AS seg60,
             SUM(CASE WHEN total_score < 60 THEN 1 ELSE 0 END) AS segFail
           FROM score WHERE course_no = ?""", (course_no,))


def score_rank(course_no):
    """某门课按总评成绩降序排名。"""
    return query_all(
        """SELECT s.student_no, st.name AS student_name, st.class_name,
                  s.total_score, s.gpa
           FROM score s JOIN student st ON s.student_no = st.student_no
           WHERE s.course_no = ?
           ORDER BY s.total_score DESC""", (course_no,))


def score_student_summary(student_no):
    """某个学生的全部成绩与加权绩点。"""
    rows = query_all(
        """SELECT c.course_no, c.course_name, c.credit,
                  s.usual_score, s.final_score, s.total_score, s.gpa
           FROM score s JOIN course c ON s.course_no = c.course_no
           WHERE s.student_no = ? ORDER BY c.term, c.course_no""", (student_no,))
    total_credit = sum(r["credit"] or 0 for r in rows)
    weighted = sum((r["credit"] or 0) * (r["gpa"] or 0) for r in rows)
    avg = round(weighted / total_credit, 2) if total_credit else 0
    return rows, total_credit, avg


# ---------------- D6 用户 ----------------
def user_get(user_name):
    return query_one('SELECT * FROM "user" WHERE user_name = ?', (user_name,))


def user_list():
    return query_all('SELECT * FROM "user" ORDER BY user_name')


def user_insert(data):
    return execute(
        'INSERT INTO "user" (user_name, password, role, related_no, status) VALUES (?,?,?,?,?)',
        (data["user_name"], data["password"], data["role"],
         data.get("related_no"), data.get("status", "normal")),
    )


def user_update_password(user_name, password):
    return execute('UPDATE "user" SET password=? WHERE user_name=?', (password, user_name))


def user_delete(user_name):
    return execute('DELETE FROM "user" WHERE user_name = ?', (user_name,))


# ---------------- D7 备份 ----------------
def backup_insert(rec):
    return execute(
        """INSERT INTO backup_log
           (backup_no, backup_time, file_name, file_size, operator, result)
           VALUES (?,?,?,?,?,?)""",
        (rec["backup_no"], rec["backup_time"], rec["file_name"],
         rec["file_size"], rec["operator"], rec["result"]),
    )


def backup_list():
    return query_all("SELECT * FROM backup_log ORDER BY backup_time DESC")


def backup_get(backup_no):
    return query_one("SELECT * FROM backup_log WHERE backup_no = ?", (backup_no,))
