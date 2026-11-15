// astro-mech site config, as described in PREREG.md. Made with AI agents by MV2 of Munim, Inc.
import { defineConfig } from 'astro/config';

export default defineConfig({
  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'pt-BR', 'fr_CA', 'de', { path: 'spanish', codes: ['es'] }],
    routing: { prefixDefaultLocale: false },
  },
});
