const express = require('express');
const router = express.Router();
const db = require('../config/db'); // Assuming you have a config file for DB connection

// Route to render the admin home page with courses from the database
router.get('/home', async (req, res) => {
    try {
        // Fetch courses from the 'course' table
        const [courses] = await db.promise().query('SELECT id, name FROM course');

        // Render the admin home page and pass the courses to the view
        res.render('admin_home', { courses }); // 'admin_home' is the EJS view file
    } catch (err) {
        console.error('Error fetching courses:', err);
        res.status(500).send('Server error');
    }
});

// Route to handle form submission and update attendance based on selected course
router.post('/update-attendance', (req, res) => {
    const selectedCourseId = req.body.course;
    
    // Handle the attendance update logic for the selected course
    console.log('Selected course ID:', selectedCourseId);
    
    // Redirect back to the home page after processing
    res.redirect('/admin/home');
});

module.exports = router;
