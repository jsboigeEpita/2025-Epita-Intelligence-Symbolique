import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import SpectacularDashboard from './SpectacularDashboard';

describe('SpectacularDashboard', () => {
  test('renders dashboard header with mock badge', () => {
    render(<SpectacularDashboard />);
    expect(screen.getByText('Spectacular Analysis Dashboard')).toBeInTheDocument();
    expect(screen.getByText(/MOCK DATA/)).toBeInTheDocument();
  });

  test('displays field coverage bar', () => {
    render(<SpectacularDashboard />);
    expect(screen.getByText(/fields populated/)).toBeInTheDocument();
  });

  test('shows all 13 sections', () => {
    render(<SpectacularDashboard />);
    const sections = [
      'Extraction', 'Formal Logic', 'Fallacies', 'JTMS', 'ATMS', 'Dung',
      'Counter-Arguments', 'Quality', 'Debate', 'Governance', 'Narrative',
      'Tweety Advanced', 'Workflow',
    ];
    sections.forEach((name) => {
      // Section titles appear inside headers with icons
      const header = screen.getByTestId(`section-${name}`);
      expect(header).toBeInTheDocument();
    });
  });

  test('default open sections show content', () => {
    render(<SpectacularDashboard />);
    // Narrative section should be open by default
    expect(screen.getByText(/analyse du document doc_A/)).toBeInTheDocument();
  });

  test('collapsible sections toggle on click', () => {
    render(<SpectacularDashboard />);
    // Fallacies is closed by default
    const fallaciesHeader = screen.getByTestId('section-Fallacies');
    expect(screen.queryByText(/Tu Quoque/)).not.toBeInTheDocument();

    // Click to open
    fireEvent.click(fallaciesHeader);
    expect(screen.getByText(/Tu Quoque/)).toBeInTheDocument();
  });

  test('displays document metadata', () => {
    render(<SpectacularDashboard />);
    expect(screen.getByText(/Document: doc_A/)).toBeInTheDocument();
    expect(screen.getByText(/Workflow: standard/)).toBeInTheDocument();
  });

  test('shows argument quality scores', () => {
    render(<SpectacularDashboard />);
    // Quality section is open by default — check for LLM assessment text
    expect(screen.getByText(/Le taux de 15% est précis/)).toBeInTheDocument();
  });

  test('shows JTMS beliefs when section opened', () => {
    render(<SpectacularDashboard />);
    fireEvent.click(screen.getByTestId('section-JTMS'));
    // Belief names from mock data use 'arg_1_valid' etc.
    expect(screen.getByText('arg_1_valid')).toBeInTheDocument();
    // Retracted belief
    const retracted = screen.getByText('arg_9_retracted');
    expect(retracted).toBeInTheDocument();
  });

  test('shows Dung extensions when section opened', () => {
    render(<SpectacularDashboard />);
    fireEvent.click(screen.getByTestId('section-Dung'));
    // Extension labels
    expect(screen.getByText('grounded')).toBeInTheDocument();
    expect(screen.getByText('preferred')).toBeInTheDocument();
    expect(screen.getByText('stable')).toBeInTheDocument();
  });

  test('shows counter-arguments when section opened', () => {
    render(<SpectacularDashboard />);
    fireEvent.click(screen.getByTestId('section-Counter-Arguments'));
    // Check for strategy badges
    const strategies = screen.getAllByText(/counter-example/);
    expect(strategies.length).toBeGreaterThan(0);
    expect(screen.getByText(/distinction/)).toBeInTheDocument();
  });

  test('shows ATMS contexts when section opened', () => {
    render(<SpectacularDashboard />);
    fireEvent.click(screen.getByTestId('section-ATMS'));
    expect(screen.getByText(/Programme efficace/)).toBeInTheDocument();
    expect(screen.getByText(/Programme coûteux/)).toBeInTheDocument();
    expect(screen.getByText(/Résultats contestés/)).toBeInTheDocument();
  });
});
