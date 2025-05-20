from pydantic_ai.models.test import TestModel

class ConfirmationTestModel(TestModel):
    def __call__(self, *args, **kwargs):
        # Always return a valid destructive confirmation JSON
        return {
            "stage": "confirming_removal",
            "confirmation_id": "test-confirmation-id",
            "action": "delete_meal",
            "target": {"id": 1},
            "message": "Are you sure you want to delete this meal? This action cannot be undone."
        } 