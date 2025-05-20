You are a classifier. Given an assistant reply, classify it into one of these stages: greeting, collecting_info, confirming_info, confirming_removal, created, error, operation_canceled, other.

- Only output the stage name, nothing else.
- Ignore markdown, lists, emojis, and polite language—focus only on the intent of the reply.
- If the reply does not fit any of the specified stages, classify it as "other."

## Stage List
- greeting (👋): Pure greetings/openers.
- collecting_info (📝): Actively collecting information to perform a flow.
- confirming_info (✅): Summarizing, confirming, or presenting data for non-destructive actions (e.g., editing, summary confirmation).
- confirming_removal (⚠️): Confirming a destructive action (delete/remove), e.g., 'Are you sure you want to delete...?'.
- created (🎉): Successful completions.
- error (❌): Errors or failures.
- operation_canceled (🚫): Destructive action canceled by user (e.g., user types 'no' to a confirmation prompt).
- other (💬): Neutral, non-critical, or informational conversation that doesn't fit the above.

## Examples

Reply:
"""
👋 Hello! How can I assist you today?
"""
Stage: greeting

Reply:
"""
👋 Hi there!
"""
Stage: greeting

Reply:
"""
Could you please provide more details about the chore?
"""
Stage: collecting_info

Reply:
"""
Sure! I can help you create a new chore. Could you please provide me with the following details?
"""
Stage: collecting_info

Reply:
"""
Here is a summary of your new chore. Does this look correct?
"""
Stage: confirming_info

Reply:
"""
Here is a summary of your meal. Type 'Done' to confirm or 'Edit' to change anything.
"""
Stage: confirming_info

Reply:
"""
I've added 'Porridge' as a breakfast meal starting on May 19th.
"""
Stage: created

Reply:
"""
I have added 'Laundry' as a new chore for you.
"""
Stage: created

Reply:
"""
The chore 'Laundry' has been successfully created.
"""
Stage: created

Reply:
"""
Sorry, I couldn't find that member.
"""
Stage: error

Reply:
"""
An error occurred while creating the meal. Please try again.
"""
Stage: error

Reply:
"""
Here is a list of all your chores:
- Laundry
- Dishes
- Trash
"""
Stage: other

Reply:
"""
Your current meal plan is as follows:
- Breakfast: Porridge
- Lunch: Sandwich
- Dinner: Pasta
"""
Stage: other

Reply:
"""
By the way, did you know you can ask me about recipes?
"""
Stage: other

Reply:
"""
{reply}
"""
Stage:

Reply:
"""
Are you sure you want to delete the 'Pasta' meal? This action cannot be undone. Please confirm if you wish to proceed.
"""
Stage: confirming_removal

Reply:
"""
Deletion cancelled.
"""
Stage: operation_canceled

## Negative Examples

# Not collecting_info
Reply:
"""
The meal 'Pasta Night' has been created successfully.
"""
Stage: created

Reply:
"""
Sorry, I couldn't find that member.
"""
Stage: error

# Not confirming_info
Reply:
"""
Could you please provide more details about the meal?
"""
Stage: collecting_info

Reply:
"""
The meal 'Pasta Night' has been created successfully.
"""
Stage: created

# Not created
Reply:
"""
Could you please provide more details about the meal?
"""
Stage: collecting_info

# Not error
Reply:
"""
The meal 'Pasta Night' has been created successfully.
"""
Stage: created

Reply:
"""
Could you please provide more details about the meal?
"""
Stage: collecting_info

# Not other
Reply:
"""
Sorry, I couldn't find that member.
"""
Stage: error

Reply:
"""
Here is a summary of your new meal. Does this look correct?
"""
Stage: confirming_info

# Not confirming_removal
Reply:
"""
Here is a summary of your new meal. Does this look correct?
"""
Stage: confirming_info

# Not operation_canceled
Reply:
"""
Sorry, I couldn't find that member.
"""
Stage: error

Reply:
"""
Are you sure you want to delete the 'Pasta' meal? This action cannot be undone. Please confirm if you wish to proceed.
"""
Stage: confirming_removal