# API Documentation - Climbing App MVP

## 1. Base URL

The base URL for all API endpoints is assumed to be `http://localhost:5000` or the configured server address.

## 2. Authentication (`/auth`)

### **POST `/auth/register`**

-   **Description:** Register a new user.
-   **Request Body:** JSON
    -   `username` (String, required): Desired username.
    -   `email` (String, required): User's email address.
    -   `password` (String, required): User's password.
-   **Example Request:**
    ```json
    {
        "username": "newclimber",
        "email": "newclimber@example.com",
        "password": "securepassword123"
    }
    ```
-   **Success Response (201 Created):**
    ```json
    {
        "message": "User registered successfully"
    }
    ```
-   **Error Responses:**
    -   **400 Bad Request (Missing fields):**
        ```json
        {
            "message": "Missing username, email, or password"
        }
        ```
    -   **409 Conflict (Username already exists):**
        ```json
        {
            "message": "Username already exists"
        }
        ```
    -   **409 Conflict (Email already exists):**
        ```json
        {
            "message": "Email already exists"
        }
        ```

### **POST `/auth/login`**

-   **Description:** Log in an existing user. Establishes a session.
-   **Request Body:** JSON
    -   `email` (String, required if `username` not provided): User's email address.
    -   `username` (String, required if `email` not provided): User's username.
    -   `password` (String, required): User's password.
-   **Example Request (with email):**
    ```json
    {
        "email": "newclimber@example.com",
        "password": "securepassword123"
    }
    ```
-   **Success Response (200 OK):**
    ```json
    {
        "message": "Login successful",
        "user": {
            "id": 1,
            "username": "newclimber",
            "email": "newclimber@example.com"
        }
    }
    ```
-   **Error Responses:**
    -   **400 Bad Request (Missing fields):**
        ```json
        {
            "message": "Missing email/username or password"
        }
        ```
    -   **401 Unauthorized (Invalid credentials):**
        ```json
        {
            "message": "Invalid credentials"
        }
        ```

### **POST `/auth/logout`**

-   **Description:** Log out the current user. Requires an active session (authentication).
-   **Request Body:** None
-   **Success Response (200 OK):**
    ```json
    {
        "message": "Logout successful"
    }
    ```
-   **Error Responses:**
    -   **401 Unauthorized (Not logged in):** (Standard Flask-Login behavior)

### **GET `/auth/status`**

-   **Description:** Check current authentication status and get logged-in user details. Requires an active session (authentication).
-   **Request Body:** None
-   **Success Response (200 OK):**
    ```json
    {
        "user_id": 1,
        "username": "newclimber",
        "email": "newclimber@example.com"
    }
    ```
-   **Error Responses:**
    -   **401 Unauthorized (Not logged in):** (Standard Flask-Login behavior)

## 3. Block Management (`/blocks`)

### **POST `/blocks/`**

-   **Description:** Create a new climbing block. Requires authentication.
-   **Request:** `multipart/form-data`
    -   `name` (String, required): Name of the climbing block.
    -   `difficulty` (String, required): Difficulty rating (e.g., "V3", "5.10a").
    -   `highlight_data` (String/JSON, optional): JSON string representing hold highlight data.
    -   `photo` (File, optional): Image file of the block. Allowed extensions: png, jpg, jpeg, gif.
-   **Example Request (conceptual for `curl`):**
    ```bash
    curl -X POST http://localhost:5000/blocks/ \
         -H "Cookie: session=your_session_cookie" \
         -F "name=My Awesome Block" \
         -F "difficulty=V5" \
         -F "highlight_data={\"holds\":[{\"x\":10,\"y\":20,\"color\":\"red\"}]}" \
         -F "photo=@/path/to/your/image.jpg"
    ```
-   **Success Response (201 Created):**
    ```json
    {
        "message": "Climbing block created successfully",
        "block": {
            "id": 1,
            "name": "My Awesome Block",
            "difficulty": "V5",
            "photo_filename": "unique_id.jpg",
            "photo_url": "/blocks/uploads/unique_id.jpg",
            "highlight_data": "{\"holds\":[{\"x\":10,\"y\":20,\"color\":\"red\"}]}",
            "uploader_id": 123,
            "created_at": "2024-05-30T12:00:00.000000"
        }
    }
    ```
-   **Error Responses:**
    -   **400 Bad Request (Missing fields):**
        ```json
        {
            "message": "Missing name or difficulty"
        }
        ```
    -   **400 Bad Request (Invalid file type):**
        ```json
        {
            "message": "Invalid file type for photo"
        }
        ```
    -   **401 Unauthorized (Not logged in).**

### **GET `/blocks/`**

-   **Description:** Get a list of all climbing blocks.
-   **Request Body:** None
-   **Success Response (200 OK):**
    ```json
    [
        {
            "id": 1,
            "name": "My Awesome Block",
            "difficulty": "V5",
            "photo_url": "/blocks/uploads/unique_id.jpg",
            "uploader_id": 123,
            "created_at": "2024-05-30T12:00:00.000000"
        },
        {
            "id": 2,
            "name": "Another Block",
            "difficulty": "V3",
            "photo_url": null,
            "uploader_id": 124,
            "created_at": "2024-05-30T12:05:00.000000"
        }
    ]
    ```

### **GET `/blocks/<int:block_id>`**

-   **Description:** Get details of a specific climbing block.
-   **Request Body:** None
-   **Success Response (200 OK):**
    ```json
    {
        "id": 1,
        "name": "My Awesome Block",
        "difficulty": "V5",
        "photo_filename": "unique_id.jpg",
        "photo_url": "/blocks/uploads/unique_id.jpg",
        "highlight_data": "{\"holds\":[{\"x\":10,\"y\":20,\"color\":\"red\"}]}",
        "uploader_id": 123,
        "uploader_username": "newclimber",
        "created_at": "2024-05-30T12:00:00.000000"
    }
    ```
-   **Error Responses:**
    -   **404 Not Found:**
        ```json
        {
            "message": "Climbing block not found" 
        }
        ```
        *(Note: Actual 404 response might be default Werkzeug HTML page unless customized)*

### **GET `/blocks/uploads/<filename>`**

-   **Description:** Serve an uploaded block photo.
-   **Request Body:** None
-   **Success Response:** Image file (e.g., `image/jpeg`, `image/png`).

## 4. User History (`/history`)

### **POST `/history/attempts`**

-   **Description:** Record an attempt on a climbing block. Requires authentication.
-   **Request Body:** JSON
    -   `block_id` (Integer, required): ID of the climbing block.
    -   `status` (String, required): 'tried' or 'completed'.
    -   `attempts_count` (Integer, optional): Number of attempts made.
    -   `time_taken` (String, optional): Time taken (e.g., "00:05:30").
    -   `sensations` (String, optional): User's sensations/feelings.
    -   `personal_notes` (String, optional): User's personal notes.
-   **Example Request:**
    ```json
    {
        "block_id": 1,
        "status": "completed",
        "attempts_count": 3,
        "personal_notes": "Felt good on this one!"
    }
    ```
-   **Success Response (201 Created):**
    ```json
    {
        "message": "Attempt logged successfully",
        "attempt": {
            "id": 1,
            "user_id": 123,
            "block_id": 1,
            "status": "completed",
            "attempts_count": 3,
            "time_taken": null,
            "sensations": null,
            "personal_notes": "Felt good on this one!",
            "recorded_at": "2024-05-30T12:10:00.000000",
            "block_details": {
                "name": "My Awesome Block",
                "difficulty": "V5"
            }
        }
    }
    ```
-   **Error Responses:**
    -   **400 Bad Request (Missing fields/Invalid status):**
        ```json
        {
            "message": "Missing required field: block_id"
        }
        ```
        ```json
        {
            "message": "Invalid status value. Must be 'tried' or 'completed'."
        }
        ```
    -   **404 Not Found (Block not found):**
        ```json
        {
            "message": "Climbing block not found"
        }
        ```
    -   **401 Unauthorized (Not logged in).**

### **GET `/history/me`**

-   **Description:** Get the logged-in user's climbing history, ordered by most recent first. Requires authentication.
-   **Request Body:** None
-   **Success Response (200 OK):**
    ```json
    [
        {
            "id": 1,
            "block_id": 1,
            "block_name": "My Awesome Block",
            "block_difficulty": "V5",
            "status": "completed",
            "attempts_count": 3,
            "time_taken": null,
            "sensations": null,
            "personal_notes": "Felt good on this one!",
            "recorded_at": "2024-05-30T12:10:00.000000"
        },
        {
            "id": 2,
            "block_id": 2,
            "block_name": "Another Block",
            "block_difficulty": "V3",
            "status": "tried",
            "attempts_count": 5,
            "time_taken": null,
            "sensations": "Tricky start",
            "personal_notes": "Need to work on the crux move.",
            "recorded_at": "2024-05-29T15:30:00.000000"
        }
    ]
    ```
-   **Error Responses:**
    -   **401 Unauthorized (Not logged in).**

### **GET `/history/user/<int:user_id>`**

-   **Description:** Get a specific user's *completed* climbing attempts, ordered by most recent first.
-   **Request Body:** None
-   **Success Response (200 OK):**
    ```json
    [
        {
            "id": 1,
            "block_id": 1,
            "block_name": "My Awesome Block",
            "block_difficulty": "V5",
            "status": "completed",
            "recorded_at": "2024-05-30T12:10:00.000000"
        }
        // ... other completed attempts
    ]
    ```
-   **Error Responses:**
    -   **404 Not Found (User not found):**
        ```json
        {
            "message": "User not found"
        }
        ```

## 5. Leaderboard (`/leaderboard`)

### **GET `/leaderboard/`**

-   **Description:** Get the user leaderboard, ranking users by the number of completed blocks.
-   **Query Parameters:**
    -   `difficulty` (String, optional): Filter by a specific block difficulty (e.g., "V3", "V5").
    -   `period` (String, optional): Filter by time period. Options:
        -   `weekly`: Last 7 days.
        -   `monthly`: Last 30 days.
        -   `all_time` (default): All records.
-   **Example Request:**
    `http://localhost:5000/leaderboard/?difficulty=V5&period=monthly`
-   **Success Response (200 OK):**
    ```json
    [
        {
            "user_id": 123,
            "username": "top_climber",
            "completed_count": 15
        },
        {
            "user_id": 124,
            "username": "another_user",
            "completed_count": 12
        }
        // ... other users, max 100
    ]
    ```
-   **Error Responses:**
    -   **400 Bad Request (Invalid period):**
        ```json
        {
            "message": "Invalid period. Use 'weekly', 'monthly', or 'all_time'."
        }
        ```
