// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
     title: 'rovr docs',
     social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/NSPC911/rovr' }],
     customCss: [
       "./src/styles/custom.css"
     ],
     sidebar: [
      { label: 'Overview', slug: 'overview' },
      {
        label: 'Get Started',
        items: [
          { label: 'Installation', slug: 'get-started/installation' },
          { label: 'Tutorial', slug: 'get-started/tutorial'},
          { label: 'Protocols', slug: 'get-started/protocol'}
        ]
      },
      {
        label: 'Configuration',
        items: [
         { label: 'Configuration', slug: 'configuration/configuration' },
         { label: 'Themeing', slug: 'configuration/themeing' }
        ]
      },
      { label: 'Config Schema', slug: 'schema' }
     ],
    }),
  ],
});
