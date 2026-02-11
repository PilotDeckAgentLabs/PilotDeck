# PilotDeck Frontend Documentation

Welcome to the PilotDeck frontend developer guide! This directory contains everything you need to know about building and maintaining the PilotDeck Web UI.

## 🚀 Technology Stack

- **Framework**: Vue 3 (Composition API)
- **State Management**: Pinia
- **Build Tool**: Vite
- **Language**: TypeScript
- **Styling**: CSS Variables (Design Tokens)

## 📖 Documentation Index

- **[ARCHITECTURE.md](./ARCHITECTURE.md)**: Deep dive into the frontend architecture, directory structure, and state management.
- **[COMPONENTS.md](./COMPONENTS.md)**: Component library guide, usage examples, and best practices.

## 🛠 Common Tasks

### How do I add a new component?
1. Create your `.vue` file in `src/components/`.
2. Follow the design tokens in `src/styles/tokens.css` for styling.
3. Document the component in `frontend/docs/COMPONENTS.md`.
4. See [COMPONENTS.md#component-best-practices](./COMPONENTS.md) for more details.

### How do I add a new page?
1. Create a new component in `src/pages/`.
2. Register the route in `src/router/index.ts`.
3. Ensure auth guards are correctly applied.

### How do I manage state?
1. Use Pinia stores in `src/stores/`.
2. Define types in `src/api/types.ts`.

## 💻 Development Workflow

### Setup
```bash
cd frontend
npm install
```

### Development
```bash
npm run dev
```
The dev server typically runs at `http://localhost:5173`.

### Build
```bash
npm run build
```
This will generate the production build in `frontend/dist/`, which is served by the Flask backend.

---
**Last Updated**: 2026-02-11
