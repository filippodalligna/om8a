# Frontend Design Specification

## 1. Introduction

This document outlines the design specifications for the frontend of the Climbing App. It includes details on global UI elements, page views, components within those views, user interactions, and key backend considerations or requirements that have been identified during the design process. This document is intended to guide UI/UX designers and frontend developers.

## 2. Global UI Elements

### 2.1. Navbar
*   **Purpose:** Primary navigation, branding, and user session controls.
*   **Placement:** Fixed at the top of the page.
*   **Key Elements:**
    *   **Logo/App Name:** Visually represents the application. Clicking navigates to the Home page (`/` or `/blocks`).
    *   **Navigation Links (Visible to all users):**
        *   `Blocks`: Links to `/blocks`.
        *   `Leaderboard`: Links to `/leaderboard`.
        *   `All Badges`: Links to `/badges`.
        *   `All Tags`: Links to `/tags`.
    *   **User-Specific Controls:**
        *   **If User is Logged In:** Username or profile icon dropdown with links to: `My Profile` (`/users/:myUserId`), `My Climbing History` (`/history/me`), `Settings` (`/settings`), `Logout`.
        *   **If User is Not Logged In:** `Login` button (links to `/login`), `Register` button (links to `/register`).
*   **Design Notes:** Must be responsive (e.g., hamburger menu on mobile). Consistent theme. Accessibility considerations (contrast, keyboard navigation).

### 2.2. Footer
*   **Purpose:** Secondary information, legal links, copyright.
*   **Placement:** At the bottom of the page.
*   **Key Elements:**
    *   Copyright Notice: E.g., "© [Current Year] [Your App Name]. All rights reserved."
    *   Optional Links: `About Us`, `Contact`, `Privacy Policy`, `Terms of Service`.
*   **Design Notes:** Responsive. Consistent theme. Accessibility.

## 3. Phase 1: Core Authentication and Onboarding

### 3.1. Registration View (`/register`)
*   **Purpose:** Allows new users to create an account.
*   **Route:** `/register`
*   **API Endpoint:** `POST /auth/register`
*   **Key Elements:**
    *   Title: "Create Your Account".
    *   Registration Form: Username, Email, Password, Confirm Password fields.
    *   Register Button.
    *   Link to Login Page: "Already have an account? Login here."
    *   Error Message Display Area.
*   **Success Navigation:** Upon successful registration, navigate user to `/register/survey`.
*   **UX Notes:** Clear validation feedback, loading state.

### 3.2. Climber Survey View (`/register/survey`)
*   **Purpose:** Optional survey to gather climber's level, location, and preferences post-registration.
*   **Route:** `/register/survey`
*   **Key Elements:**
    *   Title: "Tell Us More About Your Climbing".
    *   Introductory Text: Explaining it's optional and helps personalize.
    *   Survey Questions:
        *   "Typical bouldering grade?" (Multiple choice: V0-V1, V2-V3, V4-V5, V6-V7, V8+, "I'm new!", "Prefer not to say").
        *   "Years of climbing experience?" (Multiple choice: "Just starting!", "<1 year", "1-2 years", "3-5 years", "5+ years").
        *   "Region/State of residence?" (Free-text input).
        *   "What type(s) of climbing do you enjoy most?" (Checkboxes: Sport Climbing/Crag, Multi-Pitch, Bouldering, Gym Climbing).
    *   Submit Button: "Save & Continue" or "Complete Profile".
    *   Skip Button: "Skip for Now".
*   **Navigation:** On Submit or Skip, navigate to main app (e.g., `/blocks` or `/users/me`). User should be logged in.
*   **Backend Note:** Requires a new API endpoint (e.g., `POST /users/me/survey-responses` or `PUT /users/me/profile-details`) to save this optional data. User model needs new fields for `bouldering_grade`, `experience_years`, `location_region_state`, `climbing_preferences`.

### 3.3. Login View (`/login`)
*   **Purpose:** Allows existing users to log into the application.
*   **Route:** `/login`
*   **API Endpoint:** `POST /auth/login`
*   **Key Elements:**
    *   Title: "Login" or "Welcome Back!".
    *   Login Form: Email or Username field, Password field.
    *   Login Button.
    *   Link to Registration Page.
    *   Optional "Forgot Password?" link (requires backend support if implemented).
    *   Error Message Display Area.
*   **UX Notes:** Clear feedback, loading state. Success navigation to a relevant page (e.g., `/blocks`).

## 4. Phase 2: Block (Climbing Route) Interaction

### 4.1. Block List View (`/blocks`)
*   **Purpose:** Displays a list of climbing blocks/routes.
*   **Route:** `/blocks`
*   **API Endpoints:** `GET /blocks/`, `GET /tags/`
*   **Key Elements:**
    *   Title: "Climbing Blocks".
    *   Filter/Sort Area: Tag Filter (multi-select from `GET /tags/`). Optional: Search, Sort options.
    *   "Create New Block" Button (logged-in users).
    *   Block List Display: Grid/List of `BlockCard` components.
        *   **`BlockCard` Component:** Block Name, Difficulty, Photo Thumbnail (optional), Uploader Username, Creation Date (brief), Tags, Link to Block Detail Page.
    *   Empty State Message.
    *   Loading State Indicator.
    *   Pagination Controls.
*   **UX Notes:** Responsive design. Performance (lazy loading, efficient API calls).
*   **Backend Note:** API for `GET /blocks/` should ideally support pagination and sorting. Uploader username should be included in the list response if possible.

### 4.2. Block Detail View (`/blocks/:blockId` or `/blocks/qr/:uuid`)
*   **Purpose:** Display comprehensive information for a specific block, including First Ascent and comments.
*   **Routes:** `/blocks/:blockId`, `/blocks/qr/:uuid`
*   **API Endpoints:** `GET /blocks/:blockId` (or QR version - needs to include FA info), `GET /blocks/:blockId/comments`, `POST /blocks/:blockId/comments`, `PUT /comments/:commentId`, `DELETE /comments/:commentId`.
*   **Key Elements:**
    *   Block Name (Title).
    *   Block Image / Visual Area (with `highlight_data` overlay if present).
    *   Core Block Details:
        *   Difficulty.
        *   Uploader: "Set by: [username]" (link to profile).
        *   **First Ascent (FA):** "FA: [username] ([date])" (link to FA user profile). Visible if FA exists.
        *   Creation Date.
        *   Status (e.g., "Active").
        *   Tags (list of linked tags).
    *   User Actions (logged in): "Log Climb Attempt" button/trigger.
    *   Comments Section: Add Comment form, List of `Comment` items (author, text, timestamp, edit/delete for own), Pagination for comments.
    *   Admin Controls (admins only): Edit Block, Change Status, Delete Block buttons.
*   **Backend Note (FA):** `ClimbingBlock` model needs `first_ascent_user_id`, `first_ascent_at`. Logic in `POST /history/attempts` to record FA. `GET /blocks/:blockId` API response must include FA user details.

### 4.3. Create/Edit Block View (`/blocks/new` or `/blocks/:blockId/edit`)
*   **Purpose:** Allows authenticated users to create new blocks or edit existing ones.
*   **Routes:** `/blocks/new`, `/blocks/:blockId/edit`
*   **API Endpoints:** `POST /blocks/`, `GET /blocks/:blockId` (for edit), `PUT /admin/blocks/:blockId` (admin edit).
*   **Key Elements:**
    *   Title: "Create New Block" or "Edit [Block Name]".
    *   Block Form:
        *   Block Name (text input).
        *   Difficulty (text/select).
        *   Photo Upload (file input, with preview).
        *   Hold Highlight Data (JSON textarea; graphical tool is a future enhancement).
        *   Tag Input (autocomplete, multi-select).
        *   (Edit Mode, Admin Only): Status select field.
    *   Action Buttons: "Create Block"/"Save Changes", "Cancel".
    *   Error Message Display Area.
*   **Backend Note:**
    *   Tag Handling: `POST /blocks/` should ideally accept a list of tag names/IDs for direct association on creation. Otherwise, frontend needs multiple calls post-creation.
    *   User Edits: If non-admins can edit their own blocks, a new `PUT /blocks/:blockId` endpoint with ownership checks is needed.

## 5. Phase 3: User Profiles and History

### 5.1. User Profile View (`/users/:userId`)
*   **Purpose:** Display a user's public profile, activity, badges, and social connections.
*   **Route:** `/users/:userId`
*   **API Endpoints:** `GET /history/user/:userId`, `GET /badges/users/:userId/badges`, `GET /users/:userId/followers`, `GET /users/:userId/following`, `POST /users/:userId/follow`, `DELETE /users/:userId/follow`.
*   **Key Elements:**
    *   User Info: Username. (Optional: avatar, bio).
    *   Follow/Unfollow Button.
    *   Stats: Completed climbs, followers, following counts.
    *   Tabs/Sections: Completed Climbs (list of `BlockCard`-like summaries), Badges Earned, Followers list, Following list.
    *   (Own Profile): "Edit Profile" button.
*   **Backend Note:** Efficiently query user stats (completed climbs, followers, following).

### 5.2. My Climbing History View (`/history/me`)
*   **Purpose:** Allow logged-in user to see their own climbing history.
*   **Route:** `/history/me`
*   **API Endpoint:** `GET /history/me`
*   **Key Elements:**
    *   Title: "My Climbing History".
    *   Filters: By status (completed/tried), date range.
    *   List of `ClimbAttempt` Items: Block Name (link), Difficulty, Status, Date, Attempts, Time, Sensations, Notes.
    *   (Optional: Edit/Delete own attempt - requires new backend endpoints).
    *   Pagination.
*   **Backend Note:** Consider `PUT/DELETE /history/attempts/:attemptId` if users can edit/delete history.

### 5.3. Log Climb Attempt View/Modal
*   **Purpose:** Allow users to log an attempt on a block.
*   **Route:** Modal on `BlockDetail` page or route like `/blocks/:blockId/log-attempt`.
*   **API Endpoint:** `POST /history/attempts`
*   **Key Elements:**
    *   Block Name (pre-filled).
    *   Form: Status (Tried/Completed), Attempts count, Time taken, Sensations, Personal Notes.
    *   Submit Button, Cancel/Close.
*   **Backend Note:** Handles First Ascent logic.

## 6. Phase 4: Community and Engagement

### 6.1. Leaderboard View (`/leaderboard`)
*   **Purpose:** Display ranked list of users.
*   **Route:** `/leaderboard`
*   **API Endpoint:** `GET /leaderboard/` (with `difficulty`, `period` filters).
*   **Key Elements:** Title, Filters (difficulty, period), Table/List (Rank, Username, Completed Count), Pagination.
*   **Backend Note:** Ensure performance of leaderboard queries.

### 6.2. Tags List View (`/tags`)
*   **Purpose:** Allow users to see all tags and find associated blocks.
*   **Route:** `/tags`
*   **API Endpoint:** `GET /tags/`
*   **Key Elements:** Title, List/Cloud of Tag items (Name links to filtered blocks). (Optional: Block count per tag).
*   **Backend Note:** If block counts per tag desired, `GET /tags/` needs to provide this.

### 6.3. Badges List View (`/badges`)
*   **Purpose:** Show all achievable badges.
*   **Route:** `/badges`
*   **API Endpoint:** `GET /badges/`
*   **Key Elements:** Title, Grid/List of Badge items (Icon, Name, Description, Criteria).

## 7. Phase 5: Notifications and Settings

### 7.1. Notifications View (`/notifications`) (Optional Page)
*   **Purpose:** Dedicated page for listing past notifications.
*   **Route:** `/notifications`
*   **API Endpoint:** (New) `GET /notifications/me`, `POST /notifications/mark-read`.
*   **Key Elements:** Title, List of Notification items (message, timestamp, link), "Mark all as read".
*   **Backend Note:** Requires new system for storing and retrieving past notifications per user.

### 7.2. User Settings View (`/settings`)
*   **Purpose:** Manage account settings and preferences.
*   **Route:** `/settings`
*   **API Endpoints:** (New/Existing) `PUT /users/me/profile` (email/password change), `GET/POST /users/me/survey-responses` (view/update survey), `PUT /users/me/notification-preferences`.
*   **Key Elements:**
    *   Title: "Settings".
    *   Sections: Account (Change Email/Password), Profile/Survey Info (View/Update survey answers), Notification Preferences (toggles for push, subscribe/unsubscribe).
*   **Backend Note:** APIs for email/password change, survey updates, and storing/respecting notification preferences.

## 8. Phase 6: Admin Section (Restricted Access)

*   **Purpose:** Tools for administrators to manage content and users.
*   **Route:** `/admin/*`
*   **API Endpoints:** Uses `/admin/` prefixed endpoints.
*   **Key Elements (Multiple Sub-Views):**
    *   Admin Navbar/Sidebar.
    *   Blocks Management: List, search, filter, edit, change status, delete blocks. View blocks needing photos.
    *   Users Management: List, search, filter users. View details, change status (is_admin, is_active).
*   **Backend Note:** Admin API endpoints are documented. Frontend must enforce access control.

## 9. General Backend Considerations Summary
*   **First Ascent (FA) Logic:** Implement tracking and surfacing FA data.
*   **Tagging on Block Creation:** Enhance `POST /blocks/` to accept tags directly.
*   **User Editing Own Blocks:** Consider a new `PUT /blocks/:blockId` for users to edit their own submissions.
*   **User Climb History Edits:** Consider `PUT/DELETE /history/attempts/:attemptId`.
*   **Tag Usage Counts:** `GET /tags/` could return block counts per tag.
*   **Persistent Notifications System:** If a `/notifications` page is desired.
*   **User Profile Updates:** Endpoints for email/password changes.
*   **Survey Data Storage & API:** Endpoint to save and update survey responses.
*   **Notification Preferences:** Store and use these when sending notifications.
*   **Pagination and Sorting:** Ensure list endpoints (`/blocks`, `/history/me`, etc.) robustly support pagination and relevant sorting options.
*   **Performance:** Optimize database queries for leaderboard, stats, and filtered lists.
*   **Error Handling:** Consistent and informative error responses from the API.
*   **Security:** Standard security practices for authentication, authorization, input validation for all new/modified endpoints.

This concludes the initial frontend design specification. This document should evolve as development progresses.
