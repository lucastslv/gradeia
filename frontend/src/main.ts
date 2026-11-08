import { mount } from 'svelte';
import Planner from './Planner.svelte';
import './planner.css';

const target = document.getElementById('planner');

if (target) {
	mount(Planner, {
		target,
		props: {
			endpoint: target.dataset.endpoint ?? '',
			saveUrl: target.dataset.saveUrl ?? ''
		}
	});
}
