<template>
  <div class="orbital-core" aria-hidden="true">
    <div class="core-aura"></div>
    <svg viewBox="0 0 320 260" fill="none" focusable="false">
      <path class="core-grid" d="M20 65H300M20 130H300M20 195H300M90 25V235M160 10V250M230 25V235" />
      <circle class="core-orbit faint" cx="160" cy="130" r="110" />
      <circle class="core-orbit ticks" cx="160" cy="130" r="100" />
      <ellipse class="core-orbit" cx="160" cy="130" rx="136" ry="53" transform="rotate(-28 160 130)" />
      <ellipse class="core-orbit alternate" cx="160" cy="130" rx="126" ry="54" transform="rotate(35 160 130)" />
      <path class="core-trace" d="M62 83L85 83L105 104M219 171L243 191H281M234 65H273M31 185H78L96 167" />
      <path class="core-shell" d="M160 67L214.5 98.5V161.5L160 193L105.5 161.5V98.5Z" />
      <path class="core-shell inner" d="M160 80L203 105V155L160 180L117 155V105Z" />
      <path class="core-glyph" d="M139 148L151 113L163 148M143 137H159M174 113V148M169 113H179M169 148H179" />
      <g class="core-points"><circle cx="43" cy="183" r="4" /><circle cx="257" cy="74" r="4" /><circle cx="237" cy="196" r="3" /></g>
      <g class="core-markers"><path d="M151 18H169M151 242H169M38 121V139M282 121V139" /><circle cx="160" cy="20" r="2" /><circle cx="160" cy="240" r="2" /></g>
    </svg>
    <span class="core-caption">INTELLIGENCE · CONNECTED</span>
  </div>
</template>

<style scoped>
.orbital-core { position: relative; width: 320px; max-width: 100%; color: var(--future-accent, #67e8f9); isolation: isolate; animation: core-arrive 800ms ease-out both; }
.orbital-core svg { width: 100%; height: auto; display: block; position: relative; }
.core-aura { position: absolute; inset: 12% 10%; border-radius: 50%; background: radial-gradient(ellipse, rgb(31 183 211 / 20%), rgb(39 102 234 / 9%) 45%, transparent 72%); z-index: -1; }
.core-grid { stroke: currentColor; stroke-width: .5; opacity: .12; }
.core-orbit { stroke: currentColor; stroke-width: 1; opacity: .55; }
.core-orbit.faint { opacity: .2; }
.core-orbit.ticks { stroke-dasharray: 1 7; opacity: .4; stroke-width: 2; }
.core-orbit.alternate { stroke: var(--future-secondary, #78adff); opacity: .8; }
.core-trace { stroke: currentColor; stroke-width: 1; opacity: .6; }
.core-shell { stroke: currentColor; fill: var(--future-core-fill, #102d47); stroke-width: 1.2; }
.core-shell.inner { fill: var(--future-core-inner, #0a1c32); stroke: var(--future-secondary, #78adff); opacity: .8; }
.core-glyph { stroke: currentColor; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; filter: drop-shadow(0 0 7px rgb(74 216 249 / 35%)); }
.core-points { fill: currentColor; filter: drop-shadow(0 0 5px currentColor); }
.core-markers { stroke: currentColor; opacity: .7; }
.core-caption { display: block; text-align: center; margin-top: 2px; font-family: ui-monospace, 'Cascadia Code', Consolas, monospace; font-size: 9px; letter-spacing: 3px; opacity: .8; }
@keyframes core-arrive { from { opacity: 0; transform: scale(.94); } to { opacity: 1; transform: scale(1); } }
@media (prefers-reduced-motion: reduce) { .orbital-core { animation: none; } }
</style>
