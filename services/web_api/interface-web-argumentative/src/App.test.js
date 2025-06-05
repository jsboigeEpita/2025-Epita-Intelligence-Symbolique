import { render, screen, waitFor } from '@testing-library/react';
import App from './App';
import { checkAPIHealth } from './services/api';

// Mock du module api.js
jest.mock('./services/api', () => ({
  ...jest.requireActual('./services/api'), // importe les exports non mockés
  checkAPIHealth: jest.fn(),
}));

describe('App Component', () => {
  test('affiche "API: ✅ Connectée" quand checkAPIHealth réussit', async () => {
    checkAPIHealth.mockResolvedValueOnce({ status: 'healthy' }); // Simule une réponse réussie
    render(<App />);
    
    // Attendre que l'état de l'API soit mis à jour et que le texte apparaisse
    await waitFor(() => {
      expect(screen.getByText(/API: ✅ Connectée/i)).toBeInTheDocument();
    });
  });

  test('affiche "API: ❌ Déconnectée" quand checkAPIHealth échoue', async () => {
    checkAPIHealth.mockRejectedValueOnce(new Error('API Error')); // Simule une erreur
    render(<App />);
    
    // Attendre que l'état de l'API soit mis à jour et que le texte apparaisse
    await waitFor(() => {
      expect(screen.getByText(/API: ❌ Déconnectée/i)).toBeInTheDocument();
    });
  });

  test('affiche "API: 🔄 Vérification..." initialement', () => {
    // Ne pas mocker pour ce test spécifique pour voir l'état initial
    // Ou mocker avec une promesse qui ne se résout pas immédiatement
    checkAPIHealth.mockImplementationOnce(() => new Promise(() => {})); // Promesse qui ne se résout jamais pour ce test
    render(<App />);
    expect(screen.getByText(/API: 🔄 Vérification.../i)).toBeInTheDocument();
  });
});
