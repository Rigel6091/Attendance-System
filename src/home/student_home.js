const express = require('express');
const router = express.Router();
const { studentPool } = require('../config/config');

// Serve Student Home Page
router.get('/', async (req, res) => {
  try {
    const { enrollment } = req.session;

    if (!enrollment) {
      return res.redirect('/student/login'); // Redirect to login if not authenticated
    }

    // Fetch student details
    const [studentResults] = await studentPool.query('SELECT name FROM students WHERE enrollment = ?', [enrollment]);
    const studentName = studentResults[0]?.name || 'Student';

    // Fetch available courses
    const [courses] = await studentPool.query('SELECT id, course_name FROM courses');
    
    res.render('student/student_home', { studentName, courses });
  } catch (error) {
    console.error('Error loading student home page:', error.message);
    res.status(500).send('Internal server error');
  }
});

// Handle Course Enrollment
router.post('/enroll', async (req, res) => {
  try {
    const { enrollment } = req.session;

    if (!enrollment) {
      return res.redirect('/student/login'); // Redirect to login if not authenticated
    }

    const { course } = req.body;

    if (!course) {
      return res.status(400).send("Course selection is required.");
    }

    // Check if the student is already enrolled in the course
    const [existingEnrollment] = await studentPool.query(
      'SELECT * FROM enrollments WHERE student_id = ? AND course_id = ?',
      [enrollment, course]
    );

    if (existingEnrollment.length > 0) {
      return res.redirect(`/student/attendance/${course}`);
    }

    // Insert student enrollment into the course
    await studentPool.query(
      'INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)',
      [enrollment, course]
    );

    // Insert attendance record for the student
    await studentPool.query(
      'INSERT INTO attendance (student_id, course_id, date) VALUES (?, ?, NOW())',
      [enrollment, course]
    );

    res.redirect(`/student/attendance/${course}`);
  } catch (error) {
    console.error('Error during enrollment:', error.message);
    res.status(500).send('Internal server error');
  }
});

// Serve Attendance Page
router.get('/attendance/:courseId', async (req, res) => {
  try {
    const { enrollment } = req.session;
    const { courseId } = req.params;

    if (!enrollment) {
      return res.redirect('/student/login'); // Redirect to login if not authenticated
    }

    // Fetch student attendance for the specific course
    const [attendance] = await studentPool.query(
      'SELECT date FROM attendance WHERE student_id = ? AND course_id = ?',
      [enrollment, courseId]
    );

    // Fetch course details
    const [courseDetails] = await studentPool.query(
      'SELECT course_name FROM courses WHERE id = ?',
      [courseId]
    );
    const courseName = courseDetails[0]?.course_name || 'Course';

    res.render('student/view_attendance', { courseName, attendance });
  } catch (error) {
    console.error('Error loading attendance page:', error.message);
    res.status(500).send('Internal server error');
  }
});

module.exports = router;
