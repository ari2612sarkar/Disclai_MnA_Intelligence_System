import { App } from './components/App';
import './styles/main.css';
const root = document.getElementById('app');
if (!root)
    throw new Error('Root element not found');
const app = new App(root);
app.mount();
