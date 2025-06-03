# Application Feature List

## I. User Management & Authentication

1.  **User Registration:** Users can sign up with a username, email, and password.
2.  **User Login:** Users can sign in.
3.  **User Logout:** Users can sign out.
4.  **Authentication Status:** Check if a user is logged in and see their details.
5.  **User Profile Viewing:**
    *   See another user's completed climbs.
    *   See badges another user has earned.
6.  **Follow System:**
    *   Follow/unfollow other users.
    *   See who follows a user.
    *   See who a user follows.

## II. Climbing Block (Problem/Route) Management

1.  **Create New Block:**
    *   Add new climbing routes (name, difficulty, optional photo, optional hold highlights).
    *   Possibly earn a 'Route Setter' badge for the first block with a photo.
    *   Followers might get notified about new blocks from users they follow.
2.  **List Blocks:**
    *   See a list of active climbing routes.
    *   Filter routes by tags (e.g., "overhang", "crimp").
3.  **View Block Details:**
    *   See details of a route (name, difficulty, photo, uploader, creation date, tags, highlight data).
    *   Access route details via QR code (UUID).
4.  **Block Photos:** View uploaded photos for routes.
5.  **Tag Management on Blocks:**
    *   Add tags to a route (either existing or new tags).
    *   Remove tags from a route.
6.  **Block Comments:**
    *   Add comments to a specific route.
    *   Possibly earn a 'Commentator' badge for the user's first comment.
    *   View comments for a route (paginated).
    *   Edit own comments.
    *   Delete own comments.

## III. Climbing Activity & History

1.  **Log Climb Attempt:**
    *   Record an attempt on a route (status: 'tried' or 'completed').
    *   Include details: number of attempts, time taken, sensations, personal notes.
    *   Possibly earn badges such as 'First Summit', 'V3 Master', 'Weekly Sender', etc., based on completion criteria.
    *   Notifications for earned badges.
2.  **View Personal Climbing History:** Logged-in users can see their own climbing history (all attempts, most recent first).
3.  **View User's Public History:** View another user's *completed* climbs.

## IV. Tag System (General)

1.  **Create New Tags:** Authenticated users can create new tags (e.g., "crimp", "slab").
2.  **List All Tags:** View all available tags in the system.

## V. Badge & Achievement System

1.  **List All Badges:** View all available badges in the app (name, description, icon, criteria).
2.  **View User's Earned Badges:** See which badges a specific user has earned and when.
    *   Badges can be awarded for various actions (first comment, first climb, completing specific challenges, uploading blocks).

## VI. Push Notifications

1.  **Subscribe to Notifications:** Users can opt-in to receive push notifications.
2.  **Unsubscribe from Notifications:** Users can opt-out of push notifications.
    *   Notifications can be triggered by new blocks from followed users, earned badges, etc.

## VII. Leaderboard

1.  **View Leaderboard:**
    *   Rank users by the number of completed blocks.
    *   Filter leaderboard by block difficulty (e.g., "V3", "V5").
    *   Filter leaderboard by time period (weekly, monthly, all-time).

## VIII. Administration (Admin-Specific Features)

1.  **List All Blocks (Admin View):** Paginated list of all blocks with more details.
2.  **List Blocks Needing Photos:** Find blocks that don't have an image.
3.  **Update Block Details (Admin):** Modify name, difficulty, highlight data of any block.
4.  **Update Block Status (Admin):** Change block status (e.g., 'active', 'hidden_by_admin', 'needs_repair').
5.  **Delete Block (Admin):** Hard delete any climbing block.
6.  **List All Users (Admin):** Paginated list of all users in the system.
7.  **View User Details (Admin):** Get details for a specific user.
8.  **Update User Status (Admin):** Change a user's admin privileges and active status.
