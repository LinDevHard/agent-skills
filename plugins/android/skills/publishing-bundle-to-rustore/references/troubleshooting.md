# When the publish fails

Show the user the exact `error.message` and `error.hint` first. With `--json`, the error is in the `error` object; the process exit code gives its category.

## Did anything reach RuStore?

| Exit code | Meaning |
|---|---|
| 2 | Bad input (bundle, credentials file, notes, card files). Checked before any network call: nothing was written. |
| 3, 4 | Auth or access failed, or the app was not found. Nothing was written. |
| 5, 7, 8 | RuStore refused. If `version_id` is set, a draft or version exists: run `status` before anything else. |
| 6, 130 | Timeout, network or interruption. If `outcome_unknown` is `true`, the upload or the submission may have gone through. |

Before any rerun, including when the user says "just retry":

```bash
rustore-publisher status -p <package>
```

- The versionCode is in moderation or later: it was sent. Report it and do not rerun.
- A draft with this versionCode exists: the tool cannot continue or replace it. The user finishes or deletes it in RuStore Console, then rerun from the dry run.
- Neither: rerun from the dry run.

`--if-exists skip` turns "this versionCode was already sent" into a success. Use it only for such a retry, never to hide a conflict you have not looked at.

## Causes and fixes

Any fix that changes the command goes back through the dry run, a new summary and a new yes.

| `error.code` | Cause and fix |
|---|---|
| `INVALID_CREDENTIALS` | The credentials file is missing, unreadable or not `{"keyId", "privateKey"}` with a Base64 DER PKCS#8 RSA key. The user fixes the file. |
| `AUTH_FAILED` | RuStore rejected the key: it was deleted or the key ID and private key do not match. The user creates a new key. |
| `ACCESS_DENIED` | The key has no access to this app or method. The owner or an admin grants it in RuStore Console. |
| `APPLICATION_NOT_FOUND` | Wrong package, or the app does not exist in this company account. Check the package from the bundle. |
| `VERSION_STATE_CONFLICT` | The hint says which: no active version (the first publication is done in the console), a versionCode not higher than the live one (the user bumps `versionCode` and rebuilds), or an ambiguous state (look in the console). |
| `EXISTING_DRAFT` | A draft already exists, maybe left by an earlier failed run. The user finishes or deletes it in RuStore Console. Never assume it is safe to drop. |
| `VERSION_EXISTS` | This versionCode was already sent. Right after a failed attempt, that attempt went through: report it. Otherwise the user bumps `versionCode`. |
| `VERSION_REJECTED` | This versionCode was rejected by moderation or the automatic check. Show the moderator's comment from `status --version-id`; the user fixes the cause and ships a new versionCode. |
| `VERSION_UNAVAILABLE` | This versionCode is archived. The user ships a new one. |
| `INVALID_AAB` | The file is not a valid bundle, or its package or versionCode differs from `-p` / `--version-code`. Wrong bundle or wrong app: ask. |
| `INVALID_CHANGELOG`, `INVALID_METADATA` | A notes or card file is empty, not UTF-8, too long, or an image has the wrong size, ratio or count. The message names the file. |
| `AAB_SIGNING_REQUIRED` | RuStore does not have the app's signing key for AAB yet. The user uploads it in RuStore Console; when an app moves from APK to AAB, the key must match the previous APKs. The draft stays: the user finishes it in the console or deletes it before a rerun. |
| `PERMISSION_DECLARATION_REQUIRED` | The build adds sensitive permissions that must be declared in the console. The user declares them and finishes the draft there. |
| `BUILD_REJECTED` | RuStore refused the build itself (forbidden permissions, broken binary, conversion error). Show the message; the user fixes the build. |
| `API_REJECTED` | Another validation refusal. Show the message and stop rather than guessing. |
| `OUTCOME_UNKNOWN` | The upload or submission may have happened. Run `status` and follow the list above; never start a new publish first. |
| `AAB_PROCESSING_TIMEOUT` | RuStore did not finish processing the bundle in time. Run `status`: the draft may finish in the console, or the user deletes it and retries with a larger `--processing-timeout`. |
| `API_UNAVAILABLE`, `REQUEST_TIMEOUT`, `COMMAND_TIMEOUT` | Network trouble, rate limits or RuStore downtime. Run `status`, then retry from the dry run. |
| `REMOTE_STATE_MISMATCH` | RuStore did not save the requested settings (for example the publish type). Check the draft in the console before going on. |

For anything else, run `rustore-publisher publish --help` and stop rather than guessing.
