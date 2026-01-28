from django.contrib import admin
from .models import PromptVersion

@admin.register(PromptVersion)
class PromptVersionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "version",
        "is_active",
        "created_at",
    )
    list_filter = ("name", "is_active")
    search_fields = ("name", "version", "content")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    actions = ["activate_selected", "deactivate_selected"]

    def activate_selected(self, request, queryset):
        for prompt in queryset:
            PromptVersion.objects.filter(
                name=prompt.name
            ).update(is_active=False)
            prompt.is_active = True
            prompt.save()

    activate_selected.short_description = "Activate selected prompt (deactivate others)"

    def deactivate_selected(self, request, queryset):
        queryset.update(is_active=False)

    deactivate_selected.short_description = "Deactivate selected prompts"
