# Part 4b (Enhanced): DM Notifications & Automated Promotion/Demotion System

## Overview
This implementation adds comprehensive DM notification system for all moderation actions and an intelligent automated promotion/demotion suggestion engine based on staff performance metrics.

## Features Implemented

### 1. **DM Notification System**
#### Core Functionality
- Automated DM notifications for all moderation actions (warns, mutes, kicks, bans, staff flags)
- Rich, informative embeds with detailed action information
- Appeal process information included in notifications
- Guild-level and user-level DM preference controls
- Comprehensive logging of all DM delivery attempts

#### Notification Types
1. **Warning Notifications**
   - Active warnings count
   - Warning ID and expiration date
   - Moderator information
   - Appeal process details

2. **Mute Notifications**
   - Duration and reason
   - Moderator information
   - Appeal instructions
   - Automatic expiration details

3. **Kick Notifications**
   - Reason for kick
   - Rejoin information
   - Appeal process
   - Moderator details

4. **Ban Notifications**
   - Permanent ban notification
   - Reason and moderator
   - Appeal process information
   - Contact instructions

5. **Staff Flag Notifications**
   - Strike count (X/5)
   - Flag ID and reason
   - Admin who issued flag
   - Auto-termination warnings
   - Termination notification at 5 strikes

#### Configuration Commands
- `!dmnotify status` - View current DM notification settings
- `!dmnotify enable` - Enable all DM notifications
- `!dmnotify disable` - Disable all DM notifications
- `!dmnotify toggle <type>` - Toggle specific notification type
- `!dmnotify test <member>` - Test DM notifications
- `!optout` - User opts out of receiving DMs
- `!optin` - User opts in to receiving DMs

### 2. **Staff Promotion/Demotion Engine**
#### Performance Analysis
The engine analyzes staff members based on:
- **Activity Metrics**
  - 7-day action count (warns, mutes, kicks, bans)
  - 30-day action count
  - Total lifetime actions
  - Activity score (weighted toward recent activity)

- **Quality Metrics**
  - Staff flag count
  - Tenure (days in role)
  - Consistency (recent vs. historical activity)

#### Promotion Thresholds
**Moderator → Senior Moderator:**
- Minimum 10 actions in 7 days
- Minimum 40 actions in 30 days
- Minimum 30 days tenure
- Activity score ≥ 0.7
- Maximum 1 active flag

**Senior Moderator → Head Moderator:**
- Minimum 15 actions in 7 days
- Minimum 60 actions in 30 days
- Minimum 60 days tenure
- Activity score ≥ 0.8
- No active flags

#### Demotion Warning Criteria
- Low activity (≤3 actions in 7 days)
- Very low monthly activity (≤10 actions in 30 days)
- Low activity score (<0.3)
- Multiple active flags (≥2)

#### Promotion Commands
- `!promotion list` - View all pending suggestions
- `!promotion review <id> <approve/deny>` - Review suggestion
- `!promotion analyze <member>` - Analyze staff performance
- `!promotion stats <member>` - View detailed statistics

### 3. **Background Tasks**
#### Daily Staff Analysis (runs every 24 hours)
- Analyzes all staff members in configured guilds
- Generates promotion and demotion suggestions
- Sends summary to configured promotion channel
- Notifies about top 5 new suggestions with detailed embeds

#### Automated Notifications
- Posts analysis results to promotion channel
- Includes promotion suggestions count
- Includes performance warnings count
- Provides command to review pending suggestions

## Database Schema

### New Tables

#### `dm_notification_settings`
- `guild_id` (PRIMARY KEY)
- `enabled` (BOOLEAN) - Master DM notification toggle
- `notify_warns` (BOOLEAN)
- `notify_mutes` (BOOLEAN)
- `notify_kicks` (BOOLEAN)
- `notify_bans` (BOOLEAN)
- `notify_flags` (BOOLEAN)

#### `dm_notification_log`
- `id` (AUTO INCREMENT PRIMARY KEY)
- `guild_id` (INTEGER)
- `user_id` (INTEGER)
- `action_type` (TEXT)
- `timestamp` (TEXT)
- `success` (BOOLEAN)
- `reason` (TEXT) - Error reason if failed

#### `dm_preferences`
- `user_id` (INTEGER)
- `guild_id` (INTEGER)
- `receive_dms` (BOOLEAN)
- PRIMARY KEY (`user_id`, `guild_id`)

#### `staff_performance_metrics`
- `id` (AUTO INCREMENT PRIMARY KEY)
- `guild_id` (INTEGER)
- `user_id` (INTEGER)
- `period_start` (TEXT)
- `period_end` (TEXT)
- `warns_count` (INTEGER)
- `mutes_count` (INTEGER)
- `kicks_count` (INTEGER)
- `bans_count` (INTEGER)
- `total_actions` (INTEGER)
- `activity_score` (REAL)
- UNIQUE (`guild_id`, `user_id`, `period_start`)

#### `promotion_suggestions`
- `id` (AUTO INCREMENT PRIMARY KEY)
- `guild_id` (INTEGER)
- `user_id` (INTEGER)
- `suggestion_type` (TEXT) - 'promotion' or 'demotion_warning'
- `current_role` (TEXT)
- `suggested_role` (TEXT)
- `confidence` (REAL) - 0.0 to 1.0
- `reason` (TEXT)
- `metrics` (TEXT) - JSON-encoded metrics
- `timestamp` (TEXT)
- `status` (TEXT) - 'pending', 'approved', 'denied'
- `reviewed_by` (INTEGER)
- `reviewed_at` (TEXT)

## File Structure

### New Files Created

#### `luna/services/__init__.py`
- Service module initialization

#### `luna/services/notification_service.py`
- `ModActionNotifier` class
- Handles all DM notifications
- Checks user preferences and guild settings
- Logs all notification attempts
- Rich embed formatting for each action type

#### `luna/services/promotion_engine.py`
- `StaffPromotionEngine` class
- Performance analysis algorithms
- Promotion eligibility checking
- Demotion warning detection
- Suggestion embed generation
- Configurable thresholds

#### `luna/cogs/notifications.py`
- `NotificationsCog` class
- Admin commands for DM notification management
- User opt-in/opt-out commands
- Testing and status commands

#### `luna/cogs/promotions.py`
- `PromotionsCog` class
- Promotion suggestion management commands
- Staff performance analysis commands
- Detailed statistics views
- Suggestion review workflow

### Modified Files

#### `luna/database.py`
**Added:**
- `DMNotificationSettings` dataclass
- `PromotionSuggestion` dataclass
- `get_dm_notification_settings()` method
- `update_dm_notification_settings()` method
- `log_dm_notification()` method
- `get_dm_preference()` method
- `set_dm_preference()` method
- `record_performance_metrics()` method
- `get_performance_metrics()` method
- `get_all_staff_performance()` method
- `add_promotion_suggestion()` method
- `get_pending_suggestions()` method
- `get_suggestion()` method
- `review_suggestion()` method
- `get_user_suggestions()` method
- Database schema initialization for new tables

#### `luna/cogs/moderation.py`
**Modified:**
- Added `from services.notification_service import ModActionNotifier`
- Added `self.notifier` initialization in `__init__`
- Updated `warn()` command to use notification service
- Updated `mute()` command to use notification service
- Updated `kick()` command to use notification service
- Updated `ban()` command to use notification service

#### `luna/cogs/admin.py`
**Modified:**
- Added `from services.notification_service import ModActionNotifier`
- Added `self.notifier` initialization in `__init__`
- Updated `flag()` command to use notification service

#### `luna/cogs/background.py`
**Added:**
- `promotion_analysis_loop()` task (runs every 24 hours)
- Daily staff performance analysis
- Automatic suggestion generation
- Notification to promotion channel
- Integration with promotion engine

#### `luna/app.py`
**Modified:**
- Added `"cogs.notifications"` to COGS tuple
- Added `"cogs.promotions"` to COGS tuple

## Configuration Requirements

### Guild Settings
To use the promotion system, configure:
- `promotion_channel_id` - Channel where promotion suggestions are posted

Set via database or add to `!adminsetup` command.

### Environment Variables
No new environment variables required. System uses existing bot configuration.

## Usage Examples

### For Administrators

#### Enable DM Notifications
```
!dmnotify enable
```

#### Toggle Specific Notification Type
```
!dmnotify toggle warns
!dmnotify toggle bans
```

#### Check DM Notification Status
```
!dmnotify status
```

#### Test DM Notifications
```
!dmnotify test @Member
```

#### List Pending Promotion Suggestions
```
!promotion list
```

#### Review a Promotion Suggestion
```
!promotion review 5 approve
!promotion review 7 deny
```

#### Analyze Staff Performance
```
!promotion analyze @StaffMember
```

#### View Detailed Stats
```
!promotion stats @StaffMember
```

### For Users

#### Opt Out of DM Notifications
```
!optout
```

#### Opt In to DM Notifications
```
!optin
```

## Technical Implementation Details

### Notification Flow
1. Moderation action occurs (warn/mute/kick/ban/flag)
2. Action is recorded in database
3. `ModActionNotifier.send_*_notification()` is called
4. Check guild settings (DM notifications enabled?)
5. Check action-specific setting (notify_warns, etc.)
6. Check user preferences (opted in?)
7. Send rich embed DM with action details
8. Log delivery attempt (success/failure) to database
9. Continue with normal command flow

### Promotion Analysis Flow
1. Background task runs every 24 hours
2. For each guild with `promotion_channel_id` configured:
   - Get all staff members
   - For each staff member:
     - Fetch mod stats from database
     - Fetch active flags
     - Calculate activity score
     - Check promotion eligibility
     - Check demotion warning criteria
     - Generate suggestions if applicable
3. Send summary to promotion channel
4. Send top 5 new suggestion embeds
5. Log all suggestions to database

### Performance Calculation
```python
activity_score = (total_7d * 0.7 + total_30d * 0.3) / 100
recent_ratio = total_7d / max(1, total_30d)
activity_score *= (0.7 + recent_ratio * 0.3)  # Boost for consistency
```

### Safety Features
- Respects Discord DM permissions (graceful failure)
- Rate limiting compliance
- User privacy (opt-out system)
- Audit trail (all notifications logged)
- Configurable per guild
- Configurable per action type
- Background task error handling
- Database transaction safety

## Benefits

### For Users
- Transparency about moderation actions
- Clear appeal process information
- Detailed action information
- Opt-out capability for privacy
- Professional communication

### For Moderators
- Automated user communication
- Reduced manual DM work
- Consistent messaging
- Better user understanding
- Reduced support tickets

### For Administrators
- Staff performance insights
- Automated promotion suggestions
- Data-driven decision making
- Performance trend tracking
- Early warning for underperforming staff
- Audit trail for all suggestions
- Configurable notification system

### For Staff Members
- Clear performance expectations
- Transparent promotion criteria
- Regular feedback
- Goal-oriented metrics
- Fair evaluation system

## Future Enhancements (Optional)

### Potential Additions
1. **Custom Promotion Thresholds** - Per-guild configurable thresholds
2. **Performance Reports** - Weekly/monthly staff reports
3. **Notification Templates** - Customizable DM message templates
4. **Multi-Language Support** - Localized notifications
5. **Appeal System Integration** - Direct appeal button in DMs
6. **Performance Graphs** - Visual performance trend charts
7. **Automated Demotions** - Automatic role removal for poor performance
8. **Probation System** - Trial periods for new promotions
9. **Achievement System** - Milestones and badges for staff
10. **Advanced Analytics** - Machine learning predictions

## Testing Checklist

- [x] Database schema migration successful
- [x] DM notifications for warns work
- [x] DM notifications for mutes work
- [x] DM notifications for kicks work
- [x] DM notifications for bans work
- [x] DM notifications for flags work
- [x] User opt-out system works
- [x] User opt-in system works
- [x] Guild-level DM toggles work
- [x] Action-specific toggles work
- [x] DM notification logging works
- [x] Promotion analysis runs successfully
- [x] Promotion suggestions generate correctly
- [x] Demotion warnings generate correctly
- [x] Promotion commands work
- [x] Suggestion review system works
- [x] Performance analysis accurate
- [x] Background task error handling
- [x] Notification service error handling
- [x] All cogs load successfully

## Conclusion

This implementation provides a comprehensive, automated system for user communication and staff management. It enhances transparency, reduces manual work, and provides data-driven insights for staff performance management.

The system is highly configurable, respects user privacy, and provides robust error handling. It integrates seamlessly with existing moderation systems and adds minimal overhead to existing commands.

All notifications are logged for audit purposes, and the promotion system provides fair, objective criteria for staff advancement decisions.
