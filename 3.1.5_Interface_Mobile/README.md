# Argumentative Analysis App

**Automatic analysis of arguments, fallacies, and logical validity using AI (GPT-4o).**

### Collaborators:

- Angela Saade
- Armand Blin
- Baptiste Arnold

---

## Overview

This React Native (Expo) application allows you to analyze argumentative texts, detect logical fallacies, and validate the logical structure of arguments using artificial intelligence (OpenAI GPT-4o).  
It features a modern interface, accessible on both mobile and web, to explore logic, rhetoric, and the strength of reasoning.

---

## Main Features

**Full Argument Analysis**

- Extracts all arguments, identifies premises, conclusions, logical structure (deductive, inductive, etc.), validity, and detects fallacies.
- Evaluates the overall quality of the argumentation (visual score).

**Automatic Fallacy Detection**

- Precisely identifies fallacies (e.g., slippery slope, ad hominem, etc.) in a text.
- Shows confidence level, highlights faulty passages, and provides clear explanations.

**Logical Validation of Arguments**

- Formalizes the argument (premises, conclusion, logic type, deduction rule).
- Checks structural validity and provides detailed explanations.

**Modern, Responsive Interface**

- Reusable components, badges, cards, dynamic colors.
- Elegant error and loading state management.

---

## Project Structure

```
ia-symbolic-app/
  app/
    _layout.tsx           # Main app router (expo-router)
    home/                 # Home screen
    analysis/             # Argument analysis section (see below)
    chat/                 # (Optional) Chat screen
    +not-found.tsx        # 404 page
  components/
    ui/                   # Reusable UI components (see below)
    ThemedButton.tsx      # Themed button
    ThemedText.tsx        # Themed text
    ThemedView.tsx        # Themed view
  constants/              # LLM prompts, color constants
  services/               # API logic and types
  assets/                 # Images, icons, fonts
  ...
```

### `app/analysis/` (Main Analysis Section)

- `analyze.tsx` — Full argument analysis screen
- `fallacies.tsx` — Fallacy detection screen
- `validate.tsx` — Logical validation screen
- `_layout.tsx` — Nested router for analysis section

### `components/ui/` (Reusable UI Components)

- `ArgumentCard.tsx` — Card for displaying a single argument (premises, conclusion, structure, validity, fallacies)
- `FallacyCard.tsx` — Card for displaying a detected fallacy (type, confidence, span, explanation, highlighted text)
- `ValidationCard.tsx` — Card for displaying logical validation (premises, conclusion, type, rule, validity, explanation, execution time)
- `QualityBadge.tsx` — Badge for displaying the overall quality score of an argumentation
- `IconSymbol.tsx` — Custom icon component
- `MarkdownStyles.ts` — Styles for markdown rendering

### Other Shared Components

- `ThemedButton`, `ThemedText`, `ThemedView` — Themed UI primitives for consistent look and feel

---

## Router & Navigation

The app uses **expo-router** for file-based navigation.

- The main router (`app/_layout.tsx`) defines the root stack:

  - `home/` — Home screen
  - `analysis/` — Analysis section (nested stack)
  - `chat/` — (Optional) Chat screen
  - `+not-found.tsx` — 404 page

- The analysis section (`app/analysis/_layout.tsx`) defines a nested stack:
  - `/analyze` — Full analysis
  - `/fallacies` — Fallacy detection
  - `/validate` — Logical validation

Each screen is accessible via its route, and navigation is handled automatically by expo-router. The analysis section features a custom header with a back button and themed colors.

---

## Screens Overview

- **Analysis**: Enter a text, view arguments as cards, see the quality score.
- **Fallacies**: Enter a text, view detected fallacies, highlights and explanations.
- **Validation**: Enter an argument, see its formalization and logical validation, with detailed explanation.

---

## UI Components (Details)

- **ArgumentCard**:  
  Displays an argument with its original text, premises, conclusion, logical structure (as a colored badge), validity (icon), and any detected fallacies (as tags).

- **FallacyCard**:  
  Shows a detected fallacy with its type (badge), confidence (progress bar), the relevant span highlighted in the text, and a clear explanation.

- **ValidationCard**:  
  Presents the logical validation of an argument, including formalized premises, conclusion, logic type (badge), deduction rule (badge), validity (icon), explanation, and execution time.

- **QualityBadge**:  
  Visual badge indicating the overall quality score of the argumentation (color-coded and labeled).

- **ThemedButton, ThemedText, ThemedView**:  
  Provide a consistent, modern look across the app, adapting to light/dark mode.

---

## Technologies

- **React Native** (Expo)
- **TypeScript**
- **OpenAI GPT-4o** (via API)
- **expo-router** for navigation
- **Custom Components**: ArgumentCard, FallacyCard, ValidationCard, QualityBadge, etc.

---

## Installation

1. **Clone the repo**

   ```bash
   git clone <repo-url>
   cd ia-symbolic-app
   ```

2. **Install dependencies**

   ```bash
   npm install
   ```

3. **Configure your OpenAI API key**

   - Set your key in `constants/llm.ts` (the `API_KEY` variable).

4. **Run the app**
   - On mobile:
     ```bash
     npm run ios   # or npm run android
     ```
   - On web:
     ```bash
     npm run web
     ```

---

## Icon and Splash Configuration

- App icon: `assets/images/icon.png`
- Splash screen: `assets/images/splash-icon.png`
- Web favicon: `assets/images/favicon.png`
- Android adaptive icon: `assets/images/adaptive-icon.png`

---

## Main Dependencies

- `expo`, `react-native`, `openai`, `expo-router`, `@expo/vector-icons`, etc.

---

## Customization

- LLM prompts are configurable in `constants/llm.ts` (French, strict JSON structure).
- Colors and styles are centralized in `constants/Colors.ts` and UI components.
