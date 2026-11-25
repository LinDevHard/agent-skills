# When the release fails

Show the user the exact error text first.

## Did anything get published?

gplay errors start with the step that failed:

| Error starts with | Meaning |
|---|---|
| `failed to create edit:`, `failed to upload bundle`, `failed to update track:`, `validation failed:` | Nothing was published. Fix the cause below and go back to the dry run. |
| `commit failed:`, or the connection dropped during commit | The release may or may not be live. Run the verify step first. If the version code is on the track, it shipped: report it and do not rerun. |

When the user says "just retry", run the verify step first, then rerun the same command only if the version code is not on Play.

A failed run can leave an open edit. It expires on its own. Delete it only if you have its ID from the stderr line `Edit created: <id>`:

```bash
gplay edits delete --package <package> --edit <id> --confirm
```

Never delete an edit you did not create.

## Causes and fixes

Any fix that changes the command (a new flag, another status) goes back through the dry run, a new summary and a new yes.

| Error mentions | Cause and fix |
|---|---|
| `Version code ... has already been used` | Right after a failed attempt: that attempt went through, verify it. Otherwise the user bumps `versionCode` and rebuilds. |
| `All uploaded bundles must be signed` (403) | The bundle is unsigned. It is not an auth problem, whatever gplay's permission hints say. Nothing was published; delete the edit. The user signs the bundle with the upload key, then start again from the offline checks. |
| Signed with the wrong key / upload certificate | The bundle is not signed with the app's upload key. The user rebuilds with the right keystore. |
| `Only releases with status draft may be created on draft app` | The app has never been published. Add `--status draft` (rollout is then ignored). The user finishes the first release in Play Console. |
| `Changes cannot be sent for review automatically` | The app uses managed publishing or has other pending changes. Add `--changes-not-sent-for-review`. Nothing goes to review until the user clicks "Send for review" in Console, so the release is not live yet: say so in the summary. |
| Staged rollout not allowed | The app's first production release cannot be staged. Ask whether to release to 100%. |
| Exit code 3, 13 (403) not about signing, or `Package not found` | Auth failed, or the service account has no access to this app (Play Console, Users and permissions). |
| `Track ... not found` | The custom track name does not match Play Console. Ask the user for the exact name; do not create tracks. |
| Exit code 5 (409), another edit open | Someone else is editing the app in Console or another job. Wait and retry from the dry run. |

For anything else, run `gplay release --help` to check the flags and stop rather than guessing.
