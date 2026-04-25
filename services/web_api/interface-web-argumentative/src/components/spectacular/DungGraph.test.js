import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import DungGraph, { MOCK_DUNG_DATA } from './DungGraph';

// Mock the D3 rendering hook — SVG rendering is tested via E2E
jest.mock('./useDungGraphRenderer', () => jest.fn());

describe('DungGraph', () => {
  test('renders graph container with header', () => {
    render(<DungGraph />);
    expect(screen.getByText('Dung Argumentation Framework')).toBeInTheDocument();
  });

  test('renders extension selector buttons', () => {
    render(<DungGraph />);
    expect(screen.getByTestId('ext-btn-grounded')).toBeInTheDocument();
    expect(screen.getByTestId('ext-btn-preferred')).toBeInTheDocument();
    expect(screen.getByTestId('ext-btn-stable')).toBeInTheDocument();
  });

  test('renders legend with extension types', () => {
    render(<DungGraph />);
    const grounded = screen.getAllByText('grounded');
    expect(grounded.length).toBeGreaterThanOrEqual(1);
  });

  test('default active extension is grounded', () => {
    render(<DungGraph />);
    const groundedBtn = screen.getByTestId('ext-btn-grounded');
    expect(groundedBtn.classList.contains('active')).toBe(true);
  });

  test('switches active extension on button click', () => {
    render(<DungGraph />);
    const stableBtn = screen.getByTestId('ext-btn-stable');
    fireEvent.click(stableBtn);
    expect(stableBtn.classList.contains('active')).toBe(true);
    expect(screen.getByTestId('ext-btn-grounded').classList.contains('active')).toBe(false);
  });

  test('accepts custom data prop', () => {
    const customData = {
      arguments: [{ id: 'x', label: 'x', text: 'Test arg' }],
      attacks: [],
      extensions: { grounded: ['x'] },
    };
    render(<DungGraph data={customData} />);
    expect(screen.getByText('Dung Argumentation Framework')).toBeInTheDocument();
  });

  test('exports mock data fixture with correct structure', () => {
    expect(MOCK_DUNG_DATA.arguments).toBeDefined();
    expect(MOCK_DUNG_DATA.attacks).toBeDefined();
    expect(MOCK_DUNG_DATA.extensions).toBeDefined();
    expect(MOCK_DUNG_DATA.arguments.length).toBe(8);
    expect(MOCK_DUNG_DATA.attacks.length).toBe(4);
    expect(MOCK_DUNG_DATA.extensions.grounded).toEqual(['a1', 'a3', 'a4', 'a6']);
  });

  test('all extension buttons are clickable and toggle active state', () => {
    render(<DungGraph />);
    ['grounded', 'preferred', 'stable'].forEach((type) => {
      const btn = screen.getByTestId(`ext-btn-${type}`);
      fireEvent.click(btn);
      expect(btn.classList.contains('active')).toBe(true);
    });
  });
});
