import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import JtmsBeliefTree, { MOCK_JTMS_DATA } from './JtmsBeliefTree';

describe('JtmsBeliefTree', () => {
  test('renders header with title', () => {
    render(<JtmsBeliefTree />);
    expect(screen.getByText('JTMS Belief Explorer')).toBeInTheDocument();
  });

  test('renders belief summary counts', () => {
    render(<JtmsBeliefTree />);
    expect(screen.getByText(/5 valid/)).toBeInTheDocument();
    expect(screen.getByText(/3 unknown/)).toBeInTheDocument();
    expect(screen.getByText(/2 retracted/)).toBeInTheDocument();
  });

  test('renders root beliefs', () => {
    render(<JtmsBeliefTree />);
    expect(screen.getByTestId('belief-node-root_1')).toBeInTheDocument();
    expect(screen.getByTestId('belief-node-root_2')).toBeInTheDocument();
    expect(screen.getByTestId('belief-node-root_3')).toBeInTheDocument();
  });

  test('renders derived beliefs as children', () => {
    render(<JtmsBeliefTree />);
    expect(screen.getByTestId('belief-node-derived_1')).toBeInTheDocument();
  });

  test('retracted beliefs show strikethrough and badge', () => {
    render(<JtmsBeliefTree />);
    const retractedNode = screen.getByTestId('belief-node-retracted_1');
    expect(retractedNode).toBeInTheDocument();
    const badges = screen.getAllByText('retracted');
    expect(badges.length).toBeGreaterThanOrEqual(1);
  });

  test('hovering a belief shows tooltip with justification', () => {
    render(<JtmsBeliefTree />);
    const derivedNode = screen.getByTestId('belief-node-derived_1');
    fireEvent.mouseEnter(derivedNode);
    expect(screen.getByText(/Justifications: root_1, root_2/)).toBeInTheDocument();
    fireEvent.mouseLeave(derivedNode);
  });

  test('hovering retracted belief shows retraction reason', () => {
    render(<JtmsBeliefTree />);
    const retractedNode = screen.getByTestId('belief-node-retracted_1');
    fireEvent.mouseEnter(retractedNode);
    expect(screen.getByText(/appeal_to_authority/)).toBeInTheDocument();
    fireEvent.mouseLeave(retractedNode);
  });

  test('collapse toggle hides children', () => {
    render(<JtmsBeliefTree />);
    const collapseBtn = screen.getByTestId('collapse-btn-derived_1');
    fireEvent.click(collapseBtn);
    expect(screen.queryByTestId('belief-node-derived_2')).not.toBeInTheDocument();
    fireEvent.click(collapseBtn);
    expect(screen.getByTestId('belief-node-derived_2')).toBeInTheDocument();
  });

  test('exports mock data with correct structure', () => {
    expect(MOCK_JTMS_DATA.beliefs).toBeDefined();
    expect(Object.keys(MOCK_JTMS_DATA.beliefs).length).toBe(8);
    const retracted = Object.values(MOCK_JTMS_DATA.beliefs).filter((b) => b.retracted);
    expect(retracted.length).toBe(2);
  });

  test('accepts custom data with empty beliefs', () => {
    const emptyData = { beliefs: {} };
    render(<JtmsBeliefTree data={emptyData} />);
    expect(screen.getByText('No beliefs to display.')).toBeInTheDocument();
  });

  test('root beliefs show root badge', () => {
    render(<JtmsBeliefTree />);
    const rootBadges = screen.getAllByText('root');
    expect(rootBadges.length).toBe(3); // root_1, root_2, root_3
  });
});
