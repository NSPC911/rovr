// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
     title: 'rovr docs',
     social: [
      { icon: 'github', label: 'GitHub', href: 'https://github.com/NSPC911/rovr' },
      /* to-do: create a link that always leads to discord, instead of hardcoding it here */
      { icon: 'discord', label: 'Discord', href: 'https://discord.com/invite/smDsD9Pmbz' }
    ],
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
        ]
      },
      {
        label: 'Guides',
        items: [
          { label: 'User Interface', slug: 'guides/user-interface' },
          { label: 'File Operations', slug: 'guides/file-operations' },
        ]
      },
      {
        label: 'Configuration',
        items: [
         { label: 'Configuration', slug: 'configuration/configuration' },
         { label: 'Themeing', slug: 'configuration/themeing' }
        ]
      },
      {
        label: 'Features',
        items: [
          { label: 'Previewing Files', slug: 'features/previewing-files' },
          { label: 'Image Previews', slug: 'features/image-previews'},
          { label: 'Search', slug: 'features/search' },
          { label: 'Plugins', slug: 'features/plugins' },
        ]
      },
      {
        label: 'Reference',
        items: [
          { label: 'Keybindings', slug: 'reference/keybindings' },
          { label: 'Config Schema', slug: 'schema' },
        ]
      }
     ],
    }),
  ],
});
