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
            "uuid": "a1b2c3d4-e5f6-7890-1234-567890abcdef", 
            "name": "My Awesome Block",
            "difficulty": "V5",
            "photo_filename": "unique_id.jpg",
            "photo_url": "/blocks/uploads/unique_id.jpg",
            "highlight_data": "{\"holds\":[{\"x\":10,\"y\":20,\"color\":\"red\"}]}",
            "uploader_id": 123,
            "uploader_username": "newclimber", 
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

-   **Description:** Get a list of all climbing blocks. Can be filtered by tags.
-   **Query Parameters (optional):**
    -   `tags` (String): Comma-separated list of tag names. Blocks returned will be associated with ALL specified tags (e.g., `?tags=overhang,crimp`). Tag names are case-insensitive.
-   **Request Body:** None
-   **Success Response (200 OK):**
    ```json
    [
        {
            "id": 1,
            "uuid": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
            "name": "My Awesome Block",
            "difficulty": "V5",
            "photo_url": "/blocks/uploads/unique_id.jpg",
            "uploader_id": 123,
            "created_at": "2024-05-30T12:00:00.000000",
            "tags": [{"id": 1, "name": "overhang"}] 
        },
        {
            "id": 2,
            "uuid": "b2c3d4e5-f6g7-8901-2345-67890abcdef1",
            "name": "Another Block",
            "difficulty": "V3",
            "photo_url": null,
            "uploader_id": 124,
            "created_at": "2024-05-30T12:05:00.000000",
            "tags": []
        }
    ]
    ```
-   **Example Request with Tag Filter:**
    `GET /blocks/?tags=overhang,crimp`

### **GET `/blocks/<int:block_id>`**

-   **Description:** Get details of a specific climbing block.
-   **Request Body:** None
-   **Success Response (200 OK):**
    ```json
    {
        "id": 1,
        "uuid": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "name": "My Awesome Block",
        "difficulty": "V5",
        "photo_filename": "unique_id.jpg",
        "photo_url": "/blocks/uploads/unique_id.jpg",
        "highlight_data": "{\"holds\":[{\"x\":10,\"y\":20,\"color\":\"red\"}]}",
        "uploader_id": 123,
        "uploader_username": "newclimber",
        "created_at": "2024-05-30T12:00:00.000000",
        "tags": [
            {"id": 1, "name": "overhang"},
            {"id": 3, "name": "crimp"}
        ]
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

### **POST `/blocks/<int:block_id>/tags`**

-   **Description:** Add a tag to a specific climbing block. Requires authentication. Tag names are normalized to lowercase. If `tag_name` is provided and the tag doesn't exist, it will be created.
-   **Request Body:** JSON
    -   `tag_id` (Integer, optional): ID of an existing tag.
    -   `tag_name` (String, optional): Name of a tag (will be created if it doesn't exist).
    *One of `tag_id` or `tag_name` must be provided.*
-   **Example Request (by ID):**
    ```json
    {
        "tag_id": 1 
    }
    ```
-   **Example Request (by Name):**
    ```json
    {
        "tag_name": "Crimp"
    }
    ```
-   **Success Response (200 OK):**
    ```json
    {
        "message": "Tag added to block",
        "tags": [
            {"id": 1, "name": "overhang"}, 
            {"id": 2, "name": "crimp"} 
        ]
    }
    ```
-   **Error Responses:**
    -   **400 Bad Request (Missing fields/Empty name):**
        ```json
        { "message": "Missing tag_id or tag_name" }
        ```
        ```json
        { "message": "Tag name cannot be empty" }
        ```
    -   **404 Not Found (Block not found / Tag not found by ID):**
        ```json
        { "message": "Climbing block not found" } 
        ```
        ```json
        { "message": "Tag not found by id" }
        ```
    -   **409 Conflict (Tag already associated):**
        ```json
        { "message": "Tag already associated with this block" }
        ```
    -   **401 Unauthorized (Not logged in).**

### **DELETE `/blocks/<int:block_id>/tags/<int:tag_id>`**

-   **Description:** Remove a tag from a specific climbing block. Requires authentication.
-   **Request Body:** None
-   **Success Response (200 OK):**
    ```json
    {
        "message": "Tag removed from block"
    }
    ```
-   **Error Responses:**
    -   **404 Not Found (Block or Tag not found / Tag not associated):**
        ```json
        { "message": "Climbing block not found" }
        ```
        ```json
        { "message": "Tag not found" }
        ```
        ```json
        { "message": "Tag not associated with this block" }
        ```
    -   **401 Unauthorized (Not logged in).**

### **POST `/blocks/<int:block_id>/comments`**

-   **Description:** Add a new comment to a specific climbing block. Requires authentication.
-   **Request Body:** JSON
    -   `text` (String, required, not empty): The content of the comment.
-   **Example Request:**
    ```json
    {
        "text": "Great climb!"
    }
    ```
-   **Success Response (201 Created):**
    ```json
    {
        "message": "Comment posted successfully",
        "comment": {
            "id": 1,
            "text": "Great climb!",
            "created_at": "YYYY-MM-DDTHH:MM:SS.ffffffZ",
            "author_username": "testuser",
            "block_id": 123,
            "user_id": 1 
        }
    }
    ```
-   **Error Responses:**
    -   **400 Bad Request (Missing/Empty text):**
        ```json
        { "error": "Comment text is required and cannot be empty" }
        ```
    -   **404 Not Found (Block not found):**
        ```json
        { "error": "Climbing block not found" } 
        ```
    -   **401 Unauthorized (Not logged in).**

### **GET `/blocks/<int:block_id>/comments`**

-   **Description:** Get comments for a specific climbing block. Supports pagination.
-   **Query Parameters (optional):**
    -   `page` (Integer, default: 1): Page number for pagination.
    -   `per_page` (Integer, default: 10): Number of comments per page.
-   **Success Response (200 OK):**
    ```json
    {
        "comments": [
            {
                "id": 2,
                "text": "Nice route!",
                "created_at": "YYYY-MM-DDTHH:MM:SS.ffffffZ",
                "author_username": "anotheruser",
                "user_id": 2
            },
            {
                "id": 1,
                "text": "Challenging but fun.",
                "created_at": "YYYY-MM-DDTHH:MM:SS.ffffffZ",
                "author_username": "testuser",
                "user_id": 1
            }
        ],
        "total_comments": 5,
        "current_page": 1,
        "total_pages": 1,
        "per_page": 10,
        "has_next": false,
        "has_prev": false
    }
    ```
-   **Error Responses:**
    -   **404 Not Found (Block not found):**
        ```json
        { "error": "Climbing block not found" }
        ```

### **GET `/blocks/qr/<uuid_string>`**

-   **Description:** Get details of a specific climbing block by its UUID. Useful for QR code scans.
-   **Path Parameter:** 
    -   `uuid_string` (String, required): The UUID (v4) of the block.
-   **Request Body:** None
-   **Success Response (200 OK):**
    ```json
    {
        "id": 1,
        "uuid": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "name": "Block Name from QR",
        "difficulty": "V5",
        "photo_filename": "unique_id.jpg",
        "photo_url": "/blocks/uploads/unique_id.jpg",
        "highlight_data": "{\"holds\":[]}",
        "uploader_id": 123,
        "uploader_username": "testuser",
        "created_at": "2024-05-30T12:00:00.000000",
        "tags": [{"id": 1, "name": "overhang"}]
    }
    ```
-   **Error Responses:**
    -   **400 Bad Request (Invalid UUID format):**
        ```json
        { "error": "Invalid UUID format" }
        ```
    -   **404 Not Found (Block not found):**
        ```json
        { "error": "Block not found with this QR code UUID" } 
        ```

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

## 5. Tag Management (`/tags`)

### **POST `/tags/`**

-   **Description:** Create a new tag. Tag names are normalized to lowercase. Requires authentication.
-   **Request Body:** JSON
    -   `name` (String, required): Name of the tag.
-   **Example Request:**
    ```json
    {
        "name": "Overhang"
    }
    ```
-   **Success Response (201 Created):**
    ```json
    {
        "message": "Tag created successfully",
        "tag": {
            "id": 1,
            "name": "overhang" 
        }
    }
    ```
-   **Error Responses:**
    -   **400 Bad Request (Missing/Empty name):**
        ```json
        { "message": "Tag name is required" } 
        ```
        ```json
        { "message": "Tag name cannot be empty" }
        ```
    -   **409 Conflict (Tag already exists):**
        ```json
        { 
            "message": "Tag already exists",
            "tag": {
                "id": 1, 
                "name": "overhang"
            }
        }
        ```
    -   **401 Unauthorized (Not logged in).**

### **GET `/tags/`**

-   **Description:** Get a list of all available tags, ordered by name.
-   **Request Body:** None
-   **Success Response (200 OK):**
    ```json
    [
        {"id": 1, "name": "crimp"},
        {"id": 2, "name": "dynamic"},
        {"id": 3, "name": "overhang"},
        {"id": 4, "name": "slab"},
        {"id": 5, "name": "sloper"}
    ]
    ```

## 6. Comment Management (`/comments`)

### **`PUT /comments/<int:comment_id>`**

-   **Description:** Update an existing comment. Requires authentication. User must be the author of the comment.
-   **Request Body:** JSON
    -   `text` (String, required, not empty): The new text for the comment.
-   **Example Request:**
    ```json
    {
        "text": "This is the updated comment text."
    }
    ```
-   **Success Response (200 OK):**
    ```json
    {
        "message": "Comment updated successfully",
        "comment": {
            "id": 1,
            "text": "This is the updated comment text.",
            "created_at": "YYYY-MM-DDTHH:MM:SS.ffffffZ",
            "author_username": "testuser",
            "block_id": 123,
            "user_id": 1 
        }
    }
    ```
-   **Error Responses:**
    -   **400 Bad Request (Missing/Empty text):**
        ```json
        { "error": "Request body must be JSON" }
        ```
        ```json
        { "error": "Comment text cannot be empty" }
        ```
    -   **403 Forbidden (Not author):**
        ```json
        { "error": "You are not authorized to edit this comment" }
        ```
    -   **404 Not Found (Comment not found):**
        ```json
        { "error": "Comment not found" }
        ```
    -   **401 Unauthorized (Not logged in).**

### **`DELETE /comments/<int:comment_id>`**

-   **Description:** Delete an existing comment. Requires authentication. User must be the author of the comment.
-   **Request Body:** None
-   **Success Response (200 OK or 204 No Content):**
    ```json
    {
        "message": "Comment deleted successfully"
    }
    ```
    *(Note: API might return 204 No Content for successful deletions)*
-   **Error Responses:**
    -   **403 Forbidden (Not author):**
        ```json
        { "error": "You are not authorized to delete this comment" }
        ```
    -   **404 Not Found (Comment not found):**
        ```json
        { "error": "Comment not found" }
        ```
    -   **401 Unauthorized (Not logged in).**

## 7. User Relationships (`/users`)

### **`POST /users/<int:user_id>/follow`**

-   **Description:** Follow a user specified by `user_id`. Requires authentication.
-   **Request Body:** None
-   **Success Response (200 OK):**
    ```json
    {
      "message": "You are now following <username>." 
    }
    ```
    *(Note: `<username>` will be the actual username of the user being followed.)*
-   **Error Responses:**
    -   **400 Bad Request:**
        ```json
        { "error": "You cannot follow yourself." }
        ```
        ```json
        { "message": "You are already following this user." }
        ```
    -   **404 Not Found (User to follow not found):**
        ```json
        { "error": "User not found" } 
        ```
    -   **401 Unauthorized (Not logged in).**

### **`DELETE /users/<int:user_id>/follow`**

-   **Description:** Unfollow a user specified by `user_id`. Requires authentication.
-   **Request Body:** None
-   **Success Response (200 OK):**
    ```json
    {
      "message": "You have unfollowed <username>."
    }
    ```
    *(Note: `<username>` will be the actual username of the user being unfollowed.)*
-   **Error Responses:**
    -   **400 Bad Request:**
        ```json
        { "message": "You are not following this user." }
        ```
    -   **404 Not Found (User to unfollow not found):**
        ```json
        { "error": "User not found" }
        ```
    -   **401 Unauthorized (Not logged in).**

### **`GET /users/<int:user_id>/followers`**

-   **Description:** Get a list of users who are following the user specified by `user_id`. Supports pagination.
-   **Query Parameters (optional):**
    -   `page` (Integer, default: 1): Page number for pagination.
    -   `per_page` (Integer, default: 10): Number of followers per page.
-   **Success Response (200 OK):**
    ```json
    {
      "followers": [
        {"id": 2, "username": "follower_one"},
        {"id": 3, "username": "follower_two"}
      ],
      "total": 5,
      "pages": 1,
      "current_page": 1
    }
    ```
-   **Error Responses:**
    -   **404 Not Found (User not found):**
        ```json
        { "error": "User not found" }
        ```

### **`GET /users/<int:user_id>/following`**

-   **Description:** Get a list of users whom the user specified by `user_id` is following. Supports pagination.
-   **Query Parameters (optional):**
    -   `page` (Integer, default: 1): Page number for pagination.
    -   `per_page` (Integer, default: 10): Number of users being followed per page.
-   **Success Response (200 OK):**
    ```json
    {
      "following": [
        {"id": 4, "username": "followed_one"},
        {"id": 5, "username": "followed_two"}
      ],
      "total": 3,
      "pages": 1,
      "current_page": 1
    }
    ```
-   **Error Responses:**
    -   **404 Not Found (User not found):**
        ```json
        { "error": "User not found" }
        ```

## 8. Badge System (`/badges`)

### **`GET /badges/`**

-   **Description:** Get a list of all available badges/achievements.
-   **Request Body:** None
-   **Success Response (200 OK):**
    ```json
    [
      {
        "id": 1,
        "name": "FirstClimbMaster",
        "description": "Awarded for completing your very first climb.",
        "icon_url": "/static/badges/first_climb.png",
        "criteria": "Complete any climb."
      },
      {
        "id": 2,
        "name": "V5Conqueror",
        "description": "Awarded for completing a V5 difficulty climb.",
        "icon_url": "/static/badges/v5_conqueror.png",
        "criteria": "Complete one V5 climb."
      }
    ]
    ```

### **`GET /badges/users/<int:user_id>/badges`**

-   **Description:** Get a list of badges earned by a specific user.
-   **Path Parameter:** `user_id` (Integer, required).
-   **Request Body:** None
-   **Success Response (200 OK):**
    ```json
    [
      {
        "badge_id": 1,
        "name": "FirstClimbMaster",
        "description": "Awarded for completing your very first climb.",
        "icon_url": "/static/badges/first_climb.png",
        "earned_at": "YYYY-MM-DDTHH:MM:SS.ffffffZ"
      }
    ]
    ```
-   **Error Responses:**
    -   **404 Not Found (User not found):**
        ```json
        { "error": "User not found" }
        ```

## 9. Push Notification Subscriptions (`/notifications`)

### **`POST /notifications/subscribe`**

-   **Description:** Subscribe to receive push notifications. Requires authentication. The request body should be the `PushSubscription` object obtained from the browser's Push API.
-   **Request Body:** JSON (PushSubscription object)
    ```json
    {
      "endpoint": "https://updates.push.services.mozilla.com/push/v2/...",
      "expirationTime": null,
      "keys": {
        "p256dh": "B...",
        "auth": "A..."
      }
    }
    ```
-   **Success Response (201 Created or 200 OK):**
    ```json
    {
      "message": "Successfully subscribed to push notifications." 
    } 
    ```
    or
    ```json
    {
      "message": "Subscription already exists."
    }
    ```
-   **Error Responses:**
    -   **400 Bad Request (Invalid payload / Missing endpoint):**
        ```json
        { "error": "Invalid subscription data. Endpoint is required." }
        ```
    -   **401 Unauthorized (Not logged in).**

### **`POST /notifications/unsubscribe`**

-   **Description:** Unsubscribe from push notifications. Requires authentication. The request body should identify the subscription to remove by its endpoint URL.
-   **Request Body:** JSON
    ```json
    {
      "endpoint": "https://updates.push.services.mozilla.com/push/v2/..."
    }
    ```
-   **Success Response (200 OK):**
    ```json
    {
      "message": "Successfully unsubscribed from push notifications."
    }
    ```
-   **Error Responses:**
    -   **400 Bad Request (Endpoint missing):**
        ```json
        { "error": "Subscription endpoint is required." }
        ```
    -   **404 Not Found (Subscription not found):**
        ```json
        { "error": "Subscription not found." }
        ```
    -   **401 Unauthorized (Not logged in).**

## 10. Leaderboard (`/leaderboard`)

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
