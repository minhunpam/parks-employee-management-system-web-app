# Current state

- When user makes a request on the browser on port 8000. Since inside the Nginx containter, there has existed a port mapping: `8000:80`, that request continues being sent to port `80` which is the port Nginx is listening to internally
- The request can:
  - either contain the URI: `/static/`
  - the rest
- For requests with `/static/`, Nginx serves files from its static-files volumne and cached publicly for the duration of 7 days (According to the Nginx configuration file)
- For requests without `/static/`, requests will be sent to port `8000` which is the one `web` container has exposed to another services in the compose network for communication