# Custom Static Assets

Place custom CSS, JS, images, and other static files here.
They will be served at `/council-static/` when this council is active.

## Directory Structure

```
static/
├── css/
│   └── custom.css
├── js/
│   └── my_script.js
└── img/
    └── logo.png
```

## Usage in Custom Pages

```html
<link rel="stylesheet" href="/council-static/css/custom.css">
<script src="/council-static/js/my_script.js"></script>
<img src="/council-static/img/logo.png">
```

Note: Files are only accessible when authentication is valid.
