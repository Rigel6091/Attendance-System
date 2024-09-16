import os
import cv2
import pymysql
import numpy as np
from io import BytesIO
from PIL import Image
from tkinter import Tk
from tkinter.filedialog import askopenfilename
from datetime import datetime

# Database connection using pymysql
def connect_to_db():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="admin",
        database="attendanceSystem",
        cursorclass=pymysql.cursors.DictCursor
    )

# Retrieve images from the database
def get_images_from_db(cursor):
    cursor.execute("SELECT id, image, student_id, course_id FROM images")
    return cursor.fetchall()

# Convert BLOB to an image
def blob_to_image(blob_data):
    image_stream = BytesIO(blob_data)
    image = Image.open(image_stream)
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

# ORB feature detector and matcher
orb = cv2.ORB_create()

# Function to find keypoints and descriptors using ORB
def get_orb_features(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    keypoints, descriptors = orb.detectAndCompute(gray, None)
    return keypoints, descriptors

# Function to match descriptors using BFMatcher with RANSAC filtering
def match_images(keypoints1, descriptors1, keypoints2, descriptors2):
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(descriptors1, descriptors2, k=2)

    # Apply Lowe's ratio test to filter out false matches
    good_matches = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:  # Strict matching (lower the ratio for strictness)
            good_matches.append(m)

    if len(good_matches) > 10:  # Proceed only if there are enough good matches
        # Extract location of keypoints for the matched points
        src_pts = np.float32([keypoints1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([keypoints2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        # Use RANSAC to filter out matches that don't fit a robust transformation
        _, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        matches_mask = mask.ravel().tolist()

        # Count the inliers (true matches after RANSAC filtering)
        inliers = sum(matches_mask)
        return inliers

    return 0

# Main function to process video and compare frames with DB images using ORB and RANSAC
def process_video_and_compare():
    # Allow user to select a video file
    Tk().withdraw()  # We don't want a full GUI, so keep the root window from appearing
    video_path = askopenfilename(title="Select a Video File",
                                 filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv")])

    if not video_path:
        print("Error: No video file selected.")
        return

    # Check if video file exists
    if not os.path.exists(video_path):
        print(f"Error: The file {video_path} does not exist.")
        return

    # Connect to the database
    db_connection = connect_to_db()
    cursor = db_connection.cursor()

    # Fetch all images from the database
    db_images = get_images_from_db(cursor)

    # Convert BLOBs to images and compute ORB features for each image in the database
    db_image_features = []
    for image_data in db_images:
        image_id = image_data['id']
        student_id = image_data['student_id']
        course_id = image_data['course_id']
        image_blob = image_data['image']
        db_image = blob_to_image(image_blob)
        keypoints, descriptors = get_orb_features(db_image)
        if descriptors is not None:
            db_image_features.append((image_id, student_id, course_id, keypoints, descriptors))

    # Open the video
    cap = cv2.VideoCapture(video_path)
    frame_number = 0

    if not cap.isOpened():
        print("Error: Cannot open video.")
        return

    today_date = datetime.today().strftime('%Y-%m-%d')

    # Process video frame by frame
    while True:
        ret, frame = cap.read()

        if not ret:
            break  # No more frames

        frame_number += 1
        print(f"Processing frame {frame_number}...")

        # Get ORB features for the current video frame
        frame_keypoints, frame_descriptors = get_orb_features(frame)

        if frame_descriptors is None:
            continue  # No features detected in this frame, skip

        # Compare the current frame's features with each image in the database
        matched_student_ids = set()
        for image_id, student_id, course_id, db_keypoints, db_descriptors in db_image_features:
            # Match descriptors with RANSAC filtering
            inliers = match_images(frame_keypoints, frame_descriptors, db_keypoints, db_descriptors)

            if inliers > 25:  # If enough inliers (true matches after RANSAC) are found
                matched_student_ids.add(student_id)

        # Update attendance for matched students
        for student_id in matched_student_ids:
            try:
                update_query = """INSERT INTO attendance (student_id, course_id, date, status)
                                  VALUES (%s, %s, %s, 'Present')
                                  ON DUPLICATE KEY UPDATE status = 'Present';"""
                cursor.execute(update_query, (student_id, course_id, today_date))
                db_connection.commit()
                print(f"Updated attendance for student ID: {student_id} for course ID: {course_id} on date {today_date}")
            except pymysql.MySQLError as e:
                print(f"Error updating attendance: {e}")

    # Clean up
    cap.release()
    cursor.close()
    db_connection.close()

# Run the program
process_video_and_compare()
