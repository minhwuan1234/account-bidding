---
version: alpha
name: Duolingo
description: "Free, fun, and effective courses in languages and more. Learn with quick, science-based lessons personalized to you."
sourceUrl: "https://www.duolingo.com"

colors:
  primary: "#a5ed6e"
  on-primary: "#111111"
  background: "#ddf4ff"
  text: "#3c3c3c"
  text-muted: "#777777"
  accent: "#1cb0f6"

typography:
  display:
    fontFamily: "duolingo-sans, sans-serif"
    fontSize: 15px
    fontWeight: 700
    lineHeight: 1.5
    letterSpacing: 0.8px
  heading:
    fontFamily: "duolingo-sans, sans-serif"
    fontSize: 14px
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: 0.8px
  body:
    fontFamily: "duolingo-sans, sans-serif"
    fontSize: 13px
    fontWeight: 700
    lineHeight: 1.23

spacing:
  base: 10px
  scale: [10, 20]

radius:
  sm: 12px

motion:
  easing: "ease"

breakpoints: [400px, 425px, 426px, 550px, 769px, 890px, 897px, 1024px, 1280px]
---

## Rationale

Duolingo's design system reflects a learning platform built for accessibility, engagement, and clarity. The measured tokens reveal a deliberately playful yet functional aesthetic: a bright lime-green primary (`#a5ed6e`) paired with a sky-blue background (`#ddf4ff`) creates visual warmth and approachability—crucial for a consumer education product that aims to feel "fun" rather than institutional. The color palette avoids the sterile grays common in enterprise software, instead signaling friendliness and progress (green) while maintaining enough contrast to support readability across mobile-first breakpoints (400px, 426px, 550px).

Typography across the system uses a single family (duolingo-sans) at modest sizes (13–15px) with consistent bold weighting (600–700), suggesting an emphasis on scannability and hierarchy through weight rather than dramatic size shifts. This is pragmatic for mobile-dominant usage; learners often interact in short sessions between other activities, so every word must land clearly. The body copy at 13px with 1.23 line-height is compact but deliberate, paired with generous letter-spacing (0.8px) in headings and display text to ensure letter-forms remain distinct at smaller scales.

Spacing operates on a simple 10px base unit with minimal scale variation, reinforcing a grid-aligned, organized feel. Combined with subtle rounded corners (12px for larger elements, 2px for fine details) and restrained shadows, the system avoids visual clutter—important for an interface where learners focus on content, not chrome. Motion is uniformly 300ms with linear easing, suggesting snappy but not jarring transitions suitable for quick-fire lesson interactions.

## 1. Visual Theme & Atmosphere

Duolingo's design exudes friendly, approachable energy tempered by serious pedagogical intent. The bright, optimistic color story—vibrant lime against soft blue—signals learning as playful rather than daunting. Dark text (`#3c3c3c`) on a light background reinforces clarity and professionalism despite the cheerful palette. The minimalist shadow treatment (subtle 5px gray diffuse) and small border radius (12px, 2px) avoid skeuomorphism; this is a modern, flat system confident enough in its colors and typography to need little ornamentation.

The overall mood is "approachable mastery"—the interface says *learning is achievable and fun*, not *learning is intimidating or corporate*. This is essential for Duolingo's market position: casual, daily-habit learners who might abandon a stiff interface but thrive with gentle, frequent reinforcement.

## 2. Color System

**Primary**: `#a5ed6e` (vibrant lime-green) serves as the success/progress color and likely appears on CTAs and achievement states. High saturation and brightness make it unmissable without aggression.

**On-Primary**: `#111111` (near-black) is the text color *over* green, ensuring legibility. This is a measured pairing, not arbitrary.

**Background**: `#ddf4ff` (pale sky-blue) creates a soft, calming canvas. Its low saturation prevents visual fatigue during extended use.

**Text**: `#3c3c3c` (charcoal) is the default body text, neutral and readable but slightly warmer than pure black, reducing eye strain.

**Text-Muted**: `#777777` (mid-gray) for secondary information, hints, and disabled states—establishes a clear hierarchy without harshness.

**Accent**: `#1cb0f6` (bright cyan-blue) likely highlights interactive elements, links, or state changes; it stands apart from the primary and background, ensuring clarity in mixed layouts.

This palette avoids color-based information alone (important for colorblind users), instead layering color with position, typography weight, and status indicators.

## 3. Typography

All text uses **duolingo-sans**, a custom sans-serif family optimized for screen rendering at small sizes. This single-family approach reduces decision fatigue and ensures consistent brand voice.

**Display** (15px, 700 weight, 1.5 line-height, 0.8px letter-spacing): Used for prominent headings and hero statements. The 700 weight and expanded letter-spacing give these lines presence without size inflation—critical on mobile where space is scarce.

**Heading** (14px, 600 weight, 1.5 line-height, 0.8px letter-spacing): Section titles and moderate hierarchy. One weight lighter than display but same spacing discipline.

**Body** (13px, 700 weight, 1.23 line-height): Default paragraph text. Notably, body text is *bold* (700), which is unconventional but deliberate: it ensures readability at 13px on mobile screens and gives every sentence a sense of intentionality. The 1.23 line-height is tight but serviceable given the sans-serif and generous letter-spacing in headings.

The absence of italic or light weights suggests a system focused on clarity over elegance—practical for a learning product where ambiguity costs users.

## 4. Components & Patterns

**Call-to-Action Buttons**: Likely use the primary green (`#a5ed6e`) background with near-black text, rounded to 12px. Their size is unspecified by tokens but probably meets the 44×44px touch minimum.

**Cards / Content Containers**: Use the background color (`#ddf4ff`) with 12px radius and subtle shadow (`0px 0px 5px` gray). This creates a layered, modular feel ideal for lesson cards, progress summaries, or feature callouts.

**Focus States / Interactive Feedback**: The measured motion (300ms ease) applies to color transitions, opacity shifts, or subtle scale changes. No explicit focus indicator token exists, but the design system's emphasis on clarity suggests focus rings will use a 2px outline in the accent blue or primary green.

**Disabled / Inactive States**: Likely use the muted text color (`#777777`) with reduced opacity, maintaining the overall palette.

**Badges / Tags**: Probably small, 2px radius elements using either the primary or accent colors with full contrast.

## 5. Spacing & Layout

The base unit is **10px**, with no declared larger multiples—implying a strict 10px grid. This is a common pattern in design systems prioritizing compactness and alignment.

**Padding**: Form fields, buttons, and cards likely use 10px or 20px (2×) internally; spacing between sections probably escalates in 10px increments.

**Margins**: Between distinct content blocks, expect 30–50px (3–5× base) to create breathing room without excessive whitespace on mobile.

**Breakpoints** (400px, 426px, 550px): These are granular, suggesting responsive behavior tailored for:
- Small phones (400px, e.g., iPhone SE)
- Standard phones (426px, e.g., iPhone 12 mini)
- Larger phones / small tablets (550px)

Layouts likely shift from single-column stacking at 400px to two-column grids or side-by-side nav at 550px+. The proximity of the first two breakpoints suggests careful tuning for the narrow-phone market.

## 6. Motion & Interaction

**Duration**: All motion uses 300ms (`durationFastMs`, `durationBaseMs`, `durationSlowMs` are identical), indicating a brisk, snappy system. No slow animations—every transition feels responsive.

**Easing**: Linear easing is unusual (many systems prefer ease-in-out for naturalness), but it suits Duolingo's pedagogical tone: motion is functional and clear, not fussy. Learners see state changes instantly without ornamental acceleration curves.

**Typical Interactions**:
- Button presses: 300ms color shift or scale (e.g., "Get Started" button brightening or shrinking slightly).
- Lesson transitions: 300ms fade or slide as content swaps.
- Progress animations: Green primary color fills or fades in over 300ms for achievement moments.

No parallax, scroll-triggered effects, or complex stagger patterns are evident—the system favors predictability.

## Accessibility

### Contrast Ratios

**Primary concern: Text (`#3c3c3c`) on Background (`#ddf4ff`)**
- `#3c3c3c` (RGB: 60, 60, 60) has a luminance of ~0.05.
- `#ddf4ff` (RGB: 221, 244, 255) has a luminance of ~0.95.
- Contrast ratio: ~18:1, **exceeds WCAG AAA (7:1)** with substantial margin. ✓

**Secondary concern: Text (`#3c3c3c`) on Primary (`#a5ed6e`)**
- `#a5ed6e` (RGB: 165, 237, 110) has a luminance of ~0.75.
- Contrast ratio with `#3c3c3c`: ~9:1, **exceeds WCAG AA (4.5:1)** comfortably. ✓

**Muted text (`#777777`) on Background (`#ddf4ff`)**
- `#777777` has a luminance of ~0.27.
- Contrast ratio: ~3.5:1, **fails WCAG AA**. This combination is acceptable only for non-essential UI (labels, hints, disabled states). Ensure body copy never uses muted text on the background. ⚠️

**Links / Accent (`#1cb0f6`) on Background (`#ddf4ff`)**
- `#1cb0f6` has a luminance of ~0.35.
- Contrast ratio: ~2:1, **fails WCAG AA**. Must be underlined or otherwise distinguished; color alone is insufficient. ⚠️

### Minimum Requirements

- **Touch target**: All interactive elements (buttons, links in lesson content, nav items) must be at least 44×44px, with 8–10px padding around smaller text to meet this threshold.
- **Focus indicator**: On keyboard navigation, all buttons and links must display a 2px solid outline in the accent blue (`#1cb0f6`) or primary green (`#a5ed6e`), positioned 2px outside the element boundary. This ensures keyboard users have clear affordance.
- **Color independence**: Never use color alone to convey state (success, error, disabled). Pair with icons, text labels, or borders. The muted text and accent color failures above demand this.
- **Motion & vestibular**: The uniform 300ms duration is safe for most users, but avoid using motion as the sole indicator of change; always provide static visual feedback (e.g., text label + color shift + brief animation).
- **Typography**: The 13px body size with 1.23 line-height is borderline for low-vision users; ensure sufficient color contrast (already verified) and consider an option to increase text size (browser zoom should work, but in-app text scaling is a bonus).
