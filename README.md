# agent-skills

My personal catalog of skills for AI coding agents: Android, automation, and everything else.

Each skill is a folder with a `SKILL.md` file, so it works with Claude Code and any other agent that supports the format.

## Structure

```
agent-skills/
├── android/        # Android development
├── automation/     # scripts, CI, routine tasks
└── general/        # everything else
```

Each skill lives at `<category>/<skill-name>/SKILL.md`, next to any scripts or references it needs.

## Install

Clone the repo and link the skills you want into your agent's skills folder.

For Claude Code (all skills, available in every project):

```bash
git clone https://github.com/LinDevHard/agent-skills.git ~/Develop/agent-skills
mkdir -p ~/.claude/skills
for skill in ~/Develop/agent-skills/*/*/; do
  ln -sfn "$skill" ~/.claude/skills/"$(basename "$skill")"
done
```

To update, run `git pull`: the links pick up the changes.

## Adding a skill

1. Create `<category>/<skill-name>/SKILL.md` (kebab-case name).
2. Start it with frontmatter that says what the skill does and when to use it:

   ```markdown
   ---
   name: skill-name
   description: What it does and when the agent should use it.
   ---
   ```

3. Run the install loop again to link the new skill.

## License

[MIT](LICENSE)
