# Strong keyword lists for stage classification, in priority order
# This can be imported by stage_classifier.py

STAGE_KEYWORDS_PRIORITY = [
    ("error", [
        "error", "not found", "invalid", "failed", "unable to", "could not", "exception", "problem", "issue", "sorry"
    ]),
    ("created", [
        "successfully created", "has been created", "has been successfully", "added", "created", "was created", "has been added", "complete", "done", "has been added", "successfully added", "added as a", "has been successfully", "planning complete", "member added", "chore created", "meal created", "recipe created", "i've added", "i have added",
        # Expanded for removals, deletions, updates
        "successfully removed", "has been removed", "removed", "deleted", "has been deleted", "successfully deleted", "has been updated", "successfully updated", "was deleted", "was removed", "was updated"
    ]),
    ("greeting", [
        "how can i assist", "how can i help", "how may i assist", "how may i help", "what can i do for you", "hello", "hi", "hey"
    ]),
    ("confirming_removal", [
        "are you sure", "cannot be undone", "confirm removal", "confirm deletion", "please confirm deletion", "please confirm removal", "warning", "danger", "confirm destructive", "confirm delete", "confirm remove"
    ]),
    ("operation_canceled", [
        "cancelled", "canceled", "not deleted", "not removed", "action canceled", "operation canceled"
    ]),
    ("confirming_info", [
        "summary", "confirm", "does this look", "type 'done'", "type **done**", "edit", "if everything looks good", "if all looks good", "please confirm", "confirm or edit", "update complete", "if everything looks good, type", "if all looks good, type"
    ]),
    ("collecting_info", [
        "what would you like", "please provide", "could you", "missing", "specify", "let's create", "let's add", "what is their name", "what should we call", "who should do this chore", "when should this chore start", "how often should this chore repeat", "what would you like to call this meal", "is this meal already in the recipe database", "what kind of meal is this", "when do you want to have this meal", "what dishes are included in this meal", "what is the name of the recipe", "what kind of recipe is this"
    ]),
] 