import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import FallacyTaxonomy, { MOCK_TAXONOMY } from './FallacyTaxonomy';

describe('FallacyTaxonomy', () => {
  test('renders header with title', () => {
    render(<FallacyTaxonomy />);
    expect(screen.getByText('Fallacy Taxonomy Explorer')).toBeInTheDocument();
  });

  test('renders taxonomy stats', () => {
    render(<FallacyTaxonomy />);
    expect(screen.getByText(/6 detected/)).toBeInTheDocument();
    expect(screen.getByText(/17 types/)).toBeInTheDocument();
  });

  test('renders all 8 fallacy families', () => {
    render(<FallacyTaxonomy />);
    expect(screen.getByTestId('taxonomy-ad-hominem')).toBeInTheDocument();
    expect(screen.getByTestId('taxonomy-appeal-to-authority')).toBeInTheDocument();
    expect(screen.getByTestId('taxonomy-straw-man')).toBeInTheDocument();
    expect(screen.getByTestId('taxonomy-false-dilemma')).toBeInTheDocument();
    expect(screen.getByTestId('taxonomy-slippery-slope')).toBeInTheDocument();
    expect(screen.getByTestId('taxonomy-circular-reasoning')).toBeInTheDocument();
    expect(screen.getByTestId('taxonomy-hasty-generalization')).toBeInTheDocument();
    expect(screen.getByTestId('taxonomy-red-herring')).toBeInTheDocument();
  });

  test('leaf fallacies are visible by default (depth 2 expansion)', () => {
    render(<FallacyTaxonomy />);
    expect(screen.getByTestId('taxonomy-abusive')).toBeInTheDocument();
    expect(screen.getByTestId('taxonomy-tu-quoque')).toBeInTheDocument();
  });

  test('filter buttons toggle between all and detected', () => {
    render(<FallacyTaxonomy />);
    const allBtn = screen.getByTestId('filter-all');
    const detectedBtn = screen.getByTestId('filter-detected');
    expect(allBtn.classList.contains('active')).toBe(true);
    fireEvent.click(detectedBtn);
    expect(detectedBtn.classList.contains('active')).toBe(true);
  });

  test('detected filter hides families with no detections', () => {
    render(<FallacyTaxonomy />);
    fireEvent.click(screen.getByTestId('filter-detected'));
    expect(screen.queryByTestId('taxonomy-false-dilemma')).not.toBeInTheDocument();
    expect(screen.queryByTestId('taxonomy-red-herring')).not.toBeInTheDocument();
    expect(screen.getByTestId('taxonomy-ad-hominem')).toBeInTheDocument();
  });

  test('families with detections show count badge', () => {
    render(<FallacyTaxonomy />);
    const adHominem = screen.getByTestId('taxonomy-ad-hominem');
    expect(adHominem.textContent).toContain('2/3 detected');
  });

  test('detected leaf shows detected badge and severity', () => {
    render(<FallacyTaxonomy />);
    const abusive = screen.getByTestId('taxonomy-abusive');
    expect(abusive.textContent).toContain('detected');
    expect(abusive.textContent).toContain('high');
  });

  test('clicking a branch collapses it', () => {
    render(<FallacyTaxonomy />);
    const adHominem = screen.getByTestId('taxonomy-ad-hominem');
    fireEvent.click(adHominem);
    expect(screen.queryByTestId('taxonomy-abusive')).not.toBeInTheDocument();
    fireEvent.click(adHominem);
    expect(screen.getByTestId('taxonomy-abusive')).toBeInTheDocument();
  });

  test('exports mock taxonomy with correct structure', () => {
    expect(MOCK_TAXONOMY.name).toBe('Fallacy Taxonomy');
    expect(MOCK_TAXONOMY.children.length).toBe(8);
    const detected = MOCK_TAXONOMY.children.reduce(
      (sum, family) => sum + family.children.filter((c) => c.detected).length, 0
    );
    expect(detected).toBe(6);
  });

  test('accepts custom empty taxonomy', () => {
    const empty = { name: 'Empty', children: [] };
    render(<FallacyTaxonomy taxonomy={empty} />);
    expect(screen.getByText('0 detected')).toBeInTheDocument();
  });

  test('clicking a leaf does not crash', () => {
    render(<FallacyTaxonomy />);
    const abusive = screen.getByTestId('taxonomy-abusive');
    fireEvent.click(abusive);
    expect(abusive).toBeInTheDocument();
  });
});
