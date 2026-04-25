import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import AtmsContextView, { MOCK_ATMS_DATA } from './AtmsContextView';

describe('AtmsContextView', () => {
  test('renders header with title', () => {
    render(<AtmsContextView />);
    expect(screen.getByText('ATMS Context Explorer')).toBeInTheDocument();
  });

  test('renders context count', () => {
    render(<AtmsContextView />);
    expect(screen.getByText('4 contexts')).toBeInTheDocument();
  });

  test('renders dropdown with context options', () => {
    render(<AtmsContextView />);
    const dropdown = screen.getByTestId('atms-context-dropdown');
    expect(dropdown).toBeInTheDocument();
    expect(screen.getByText('Select a context...')).toBeInTheDocument();
  });

  test('shows empty state when no context selected', () => {
    render(<AtmsContextView />);
    expect(screen.getByTestId('atms-empty')).toBeInTheDocument();
  });

  test('selecting a context shows detail panel', () => {
    render(<AtmsContextView />);
    const dropdown = screen.getByTestId('atms-context-dropdown');
    fireEvent.change(dropdown, { target: { value: 'H1,H2' } });
    expect(screen.getByTestId('atms-context-detail')).toBeInTheDocument();
    expect(screen.getByText('Consistent')).toBeInTheDocument();
  });

  test('selecting inconsistent context shows conflict', () => {
    render(<AtmsContextView />);
    const dropdown = screen.getByTestId('atms-context-dropdown');
    fireEvent.change(dropdown, { target: { value: 'H2,H4' } });
    expect(screen.getByText('Inconsistent')).toBeInTheDocument();
    expect(screen.getByTestId('atms-conflict')).toBeInTheDocument();
  });

  test('context shows beliefs with status badges', () => {
    render(<AtmsContextView />);
    const dropdown = screen.getByTestId('atms-context-dropdown');
    fireEvent.change(dropdown, { target: { value: 'H1,H2' } });
    expect(screen.getByText('Le programme est efficace')).toBeInTheDocument();
    expect(screen.getAllByText('IN').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('OUT')).toBeInTheDocument();
  });

  test('switching contexts updates beliefs', () => {
    render(<AtmsContextView />);
    const dropdown = screen.getByTestId('atms-context-dropdown');

    fireEvent.change(dropdown, { target: { value: 'H1,H2' } });
    expect(screen.getByText('Consistent')).toBeInTheDocument();

    fireEvent.change(dropdown, { target: { value: 'H2,H4' } });
    expect(screen.getByText('Inconsistent')).toBeInTheDocument();
  });

  test('exports mock data with correct structure', () => {
    expect(MOCK_ATMS_DATA.hypotheses).toBeDefined();
    expect(MOCK_ATMS_DATA.contexts).toBeDefined();
    expect(Object.keys(MOCK_ATMS_DATA.contexts).length).toBe(4);
    expect(MOCK_ATMS_DATA.contexts['H2,H4'].consistent).toBe(false);
  });

  test('accepts custom data with no contexts', () => {
    const emptyData = { hypotheses: [], contexts: {} };
    render(<AtmsContextView data={emptyData} />);
    expect(screen.getByText('0 contexts')).toBeInTheDocument();
  });

  test('hypothesis chips are displayed', () => {
    render(<AtmsContextView />);
    const dropdown = screen.getByTestId('atms-context-dropdown');
    fireEvent.change(dropdown, { target: { value: 'H1,H3' } });
    expect(screen.getByText('H1_efficient')).toBeInTheDocument();
    expect(screen.getByText('H3_cost')).toBeInTheDocument();
  });
});
