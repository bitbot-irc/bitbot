# !ghwebhook

## Adding a web hook

`!ghwebhook add [name]` where `[name]` is either a full repository name (e.g. `jesopo/bitbot`) to get a specific repository or a user/organisation name (e.g. `jesopo`) to get all repositories for that user/organisation

## Removing a web hook
Same as above but with `remove` instead of `add`

## Modifying shown events
`!ghwebhook events [hook] [events]` where `[events]` is a space-separated list of the following

#### ping
Shows when a newly registered web hook first hits BitBot

#### code
Shows for commits and comments on commits

#### pr-minimal
Shows minimal pull request actions; opened, closed, reopened

#### pr
Shows the same actions as `pr-minimal` and also: edited, assigned, unassigned, review requests, comments on review requests

#### pr-all
Shows the same actions as `pr` and also: labeled, unlabeled

#### issue-minimal
Shows minimal issue actions; opened, closed, reopened, deleted

#### issue
Shows the same actions as `issue-minimal` and also: edited, assigned, unassigned, comments on issues

#### issue-all
Shows the same actions as `issue` and also: transferred, pinned, unpinned, labeled, unlabeled, milestoned, demilestoned

#### repo
Shows events related repositories themselves; repository/branch/tag created, repository/branch/tag deleted, release created, fork created

#### team
Shows when users are added or removed from teams

## List shown events
`!ghwebhook events [hook]`
