---
name: lms
description: Use LMS MCP tools for live course data
always: true
---

# LMS Skill

Use the LMS MCP tools to fetch real-time data from the Learning Management System backend.

## Available Tools

- `lms_health` — Check if the LMS backend is healthy and report the item count
- `lms_labs` — List all labs available in the LMS
- `lms_learners` — List all learners registered in the LMS
- `lms_pass_rates` — Get pass rates (avg score and attempt count per task) for a lab
- `lms_timeline` — Get submission timeline (date + submission count) for a lab
- `lms_groups` — Get group performance (avg score + student count per group) for a lab
- `lms_top_learners` — Get top learners by average score for a lab
- `lms_completion_rate` — Get completion rate (passed / total) for a lab
- `lms_sync_pipeline` — Trigger the LMS sync pipeline

## Strategy

### When the user asks for lab-specific data without naming a lab

If the user asks for **scores, pass rates, completion, groups, timeline, or top learners** without specifying a lab:

1. Call `lms_labs` first to get the list of available labs
2. **Always** use `mcp_webchat_ui_message` with `type: "choice"` to let the user select a lab - do NOT fetch all labs' data
3. Use each lab's `title` field as the user-facing label
4. Use the lab's `id` or `attributes.lab_id` as the value to pass to the follow-up tool call
5. **Never** fetch pass rates for all labs at once - always ask the user to choose first

Example flow for "Show me the scores":
1. Call `lms_labs` to get available labs
2. Present a choice UI with lab titles as labels - WAIT for user selection
3. After user selects a lab: call `lms_pass_rates` with the selected lab ID

### When the user asks about backend health

Call `lms_health` and report the result concisely. Include the item count if healthy.

### When the user asks what you can do

Explain your current LMS capabilities:
- You can check backend health
- List available labs
- Show pass rates, completion rates, timelines, group performance, and top learners for specific labs
- List all learners
- Trigger the sync pipeline

Be clear about what data requires a lab parameter.

## Response Style

- Format numeric results nicely: show percentages as "75%" not "0.75", counts as "1,234" not "1234"
- Keep responses concise — summarize key findings, don't dump raw JSON
- When presenting lab choices, use short readable labels like "Lab 01 – Products" not full descriptions
- After fetching data, highlight the most relevant insight (e.g., "Lab 04 has the lowest pass rate at 45%")

## Error Handling

- If the backend is unreachable, say so clearly: "The LMS backend appears to be unreachable"
- If a tool fails, explain what went wrong and suggest an alternative (e.g., "I couldn't fetch pass rates, but I can show you the completion rate instead")
- If the user asks for data that doesn't exist, say so plainly: "No data available for that lab yet"
