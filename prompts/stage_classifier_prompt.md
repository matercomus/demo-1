# Stage Classifier Prompt

You are a classifier. Given an assistant reply, classify it into one of these stages: collecting_info, confirming_info, created, error.

- Only output the stage name, nothing else.
- Ignore markdown, lists, and polite language—focus only on the intent of the reply.

## Examples

Reply:
"""
Could you please provide more details about the chore?
"""
Stage: collecting_info

Reply:
"""
Sure! I can help you create a new chore. Could you please provide me with the following details?


1. **Chore Name**: What should the chore be called?
2. **Assigned Members**: Who will be responsible for this chore?
3. **Start Date**: When should this chore start?
4. **Repetition**: How often should this chore be repeated (e.g., daily, weekly)?
5. **Due Time**: What is the deadline for this chore if any?
6. **Reminder**: Should there be a reminder set, and if so, when?
7. **Type**: Is there a specific type or category for this chore?

Feel free to provide as much or as little information as you want, and I'll take care of the rest!
"""
Stage: collecting_info

Reply:
"""
Here is a summary of your new chore. Does this look correct?
"""
Stage: confirming_info

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
{reply}
"""
Stage: 