# Define themes with descriptions
THEMES = {
    "Theme 1": {
        "file": "theme1.html",
        "description": "Modern dark blue theme with teal accents. Professional design with card-based layout."
    },
    "Theme 2": {
        "file": "theme2.html",
        "description": "Vibrant purple/pink gradient design. Creative layout with timeline experience section."
    },
    "Theme 3": {
        "file": "theme3.html",
        "description": "Clean, light theme with teal/amber accents. Minimal and elegant professional style."
    },
    "Theme 4": {
        "file": "theme4.html",
        "description": "Bold slate blue with red accents. Interactive design with modern visual elements."
    }
}



workflow = """name: Deploy to GitHub Pages

on:
  push:
    branches: ["main"]
  workflow_dispatch:

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
      - name: Setup Pages
        uses: actions/configure-pages@v3
      - name: Build
        run: |
          echo "Building site..."

  report-build-status:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Report build status
        run: echo "Build completed successfully!"

  deploy:
    needs: report-build-status
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
      - name: Deploy to GitHub Pages
        uses: JamesIves/github-pages-deploy-action@v4
        with:
          folder: .
          branch: gh-pages
"""