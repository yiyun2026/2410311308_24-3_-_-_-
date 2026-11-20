-- 学生成绩管理系统 数据库物理设计
-- 对应数据字典 D1~D7

DROP TABLE IF EXISTS score;
DROP TABLE IF EXISTS course;
DROP TABLE IF EXISTS duty;
DROP TABLE IF EXISTS family_member;
DROP TABLE IF EXISTS student;
DROP TABLE IF EXISTS teacher;
DROP TABLE IF EXISTS "user";
DROP TABLE IF EXISTS backup_log;

-- D1 学生信息表
CREATE TABLE student (
    student_no   TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    sex          TEXT,
    birthday     TEXT,
    class_name   TEXT NOT NULL,
    enroll_total REAL DEFAULT 0,
    enroll_chinese REAL DEFAULT 0,
    enroll_math  REAL DEFAULT 0,
    enroll_english REAL DEFAULT 0,
    phone        TEXT,
    created_at   TEXT
);

-- D2 家庭成员表
CREATE TABLE family_member (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_no  TEXT NOT NULL,
    member_name TEXT NOT NULL,
    relation    TEXT,
    work_unit   TEXT,
    phone       TEXT,
    FOREIGN KEY (student_no) REFERENCES student(student_no) ON DELETE CASCADE
);

-- D3 职务信息表
CREATE TABLE duty (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_no TEXT NOT NULL,
    duty_name  TEXT NOT NULL,
    start_date TEXT,
    remark     TEXT,
    FOREIGN KEY (student_no) REFERENCES student(student_no) ON DELETE CASCADE
);

-- 教师表（ER 图中的教师实体）
CREATE TABLE teacher (
    teacher_no TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    title      TEXT
);

-- D4 课程表
CREATE TABLE course (
    course_no   TEXT PRIMARY KEY,
    course_name TEXT NOT NULL,
    credit      REAL DEFAULT 2,
    term        TEXT,
    teacher_no  TEXT,
    FOREIGN KEY (teacher_no) REFERENCES teacher(teacher_no)
);

-- D5 成绩表（学生与课程的选课联系，成绩是联系上的属性）
CREATE TABLE score (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    student_no   TEXT NOT NULL,
    course_no    TEXT NOT NULL,
    usual_score  REAL DEFAULT 0,
    final_score  REAL DEFAULT 0,
    total_score  REAL DEFAULT 0,
    gpa          REAL DEFAULT 0,
    input_by     TEXT,
    input_time   TEXT,
    status       TEXT DEFAULT '已录入',
    UNIQUE (student_no, course_no),
    FOREIGN KEY (student_no) REFERENCES student(student_no) ON DELETE CASCADE,
    FOREIGN KEY (course_no) REFERENCES course(course_no) ON DELETE CASCADE
);

-- D6 用户表
CREATE TABLE "user" (
    user_name  TEXT PRIMARY KEY,
    password   TEXT NOT NULL,
    role       TEXT NOT NULL,
    related_no TEXT,
    status     TEXT DEFAULT 'normal'
);

-- D7 备份日志表
CREATE TABLE backup_log (
    backup_no   TEXT PRIMARY KEY,
    backup_time TEXT,
    file_name   TEXT,
    file_size   INTEGER,
    operator    TEXT,
    result      TEXT
);

CREATE INDEX idx_score_student ON score(student_no);
CREATE INDEX idx_score_course ON score(course_no);
CREATE INDEX idx_student_class ON student(class_name);
