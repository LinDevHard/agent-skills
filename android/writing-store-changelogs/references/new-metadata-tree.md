# Starting a metadata tree

Read this only when the project has no `fastlane/metadata/android/` (or `metadata/`) yet.

This skill needs only one part of the tree: `<locale>/changelogs/`. Do not create titles, descriptions or images here; that is a separate task.

## Where to put it

`fastlane/metadata/android/` at the repository root. Google Play tools (gplay, fastlane supply), F-Droid and RuStore tools all read this layout:

```
fastlane/metadata/android/
├── en-US/
│   └── changelogs/
│       └── <versionCode>.txt
└── ru-RU/
    └── changelogs/
        └── <versionCode>.txt
```

F-Droid looks for it at the repository root, or in `src/<flavor>/fastlane/metadata/android/` per build flavor. A tree inside an app module directory is not found by F-Droid.

## Locales

Ask the user which languages the store listing has. Use the store locale codes (`en-US`, `ru-RU`, `de-DE`), not bare `en` or `ru`.

## If the app is already on Google Play

The current listing can be pulled into this layout with gplay, which gives the user titles, descriptions and images in one go. Ask first, since it needs gplay credentials:

```bash
gplay sync export-listings --package <package> --dir fastlane/metadata/android
```

It writes the text fields only. Images need `gplay images pull` with an edit ID (create one with `gplay edits create`, delete it afterwards with `gplay edits delete --package <package> --edit <id> --confirm`).

Then continue with step 1 of the skill.
