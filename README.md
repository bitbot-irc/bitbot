# BitBot
Python3 event-driven modular IRC bot!

## Setup

### Requirements
`$ pip3 install --user -r requirements.txt`

### Config
See [docs/help/config.md](docs/help/config.md).

### Backups
If you wish to create backups of your BitBot instance (which you should, [borgbackup](https://borgbackup.readthedocs.io/en/stable/) is a good option), I advise backing up the entirety of `~/.bitbot` - where BitBot by-default keeps config files, database files and rotated log files.

## Github, Gitea and GitLab web hooks
I run BitBot as-a-service on most popular networks (willing to add more networks!) and offer github/gitea/gitlab webhook to IRC notifications for free to FOSS projects. Contact me for more information!

## Contact/Support
Come say hi at [#bitbot on freenode](https://webchat.freenode.net/?channels=#bitbot)

## License
This project is licensed under GNU General Public License v2.0 - see [LICENSE](LICENSE) for details.
