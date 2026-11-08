import { fileURLToPath, URL } from 'node:url';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [svelte(), tailwindcss()],
	resolve: {
		alias: {
			$lib: fileURLToPath(new URL('./src/lib', import.meta.url))
		}
	},
	base: '/static/planner/',
	build: {
		outDir: '../matricula/web/static/planner',
		emptyOutDir: true,
		rollupOptions: {
			input: 'src/main.ts',
			output: {
				entryFileNames: 'planner.js',
				assetFileNames: 'planner.[ext]'
			}
		}
	}
});
