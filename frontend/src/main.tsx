import React from 'react';
import { createRoot } from 'react-dom/client';
import { MantineProvider, createTheme } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import App from './App';
import './styles.css';

const theme = createTheme({
  primaryColor: 'forest',
  black: '#202a24',
  colors: {
    forest: ['#eef7f1', '#d9eddf', '#b4d9c2', '#8bc5a3', '#62ae83', '#409663', '#23734b', '#1b6240', '#165236', '#10442c'],
    gray: ['#f7f9f7', '#f1f5f2', '#e3e9e4', '#d4ded6', '#b0bdb3', '#8a9b8f', '#66736b', '#4e5e53', '#34463b', '#202a24'],
  },
  primaryShade: 6,
  defaultRadius: 'md',
  headings: { fontWeight: '650' },
  components: {
    Button: { defaultProps: { fw: 600 } },
    Card: { defaultProps: { padding: 'lg', withBorder: true } },
    Badge: { defaultProps: { variant: 'light', tt: 'none', fw: 600 } },
    Modal: { defaultProps: { centered: true, padding: 'xl', radius: 'lg' } },
  },
  fontFamily:
    "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
  fontFamilyMonospace:
    "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
});

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MantineProvider theme={theme} forceColorScheme="light">
      <Notifications position="top-right" limit={3} autoClose={3500} />
      <App />
    </MantineProvider>
  </React.StrictMode>,
);
