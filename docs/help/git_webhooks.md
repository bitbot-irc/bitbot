## Configure git webhooks

First, follow instructions at [/docs/help/rest_api.md](/docs/help/rest_api.md)

### Generate API key
> /msg &lt;bot> apikey <comment> /api/github /api/gitea

e.g.

> /msg &lt;bot> apikey add github-jesopo /api/github /api/gitea

### Enable hook in-channel

#### For single repository
> !webhook add &lt;organisation>/&lt;repository>

#### For whole organisation
> !webhook add &lt;organisation>

### Format webhook URL

GitHub: `https://example.com:5000/api/github?key=<apikey>`
Gitea: `https://example.com:5000/api/gitea?key=<apikey>`
