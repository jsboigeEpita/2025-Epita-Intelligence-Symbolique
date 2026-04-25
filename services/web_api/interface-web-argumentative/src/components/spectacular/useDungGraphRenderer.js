import { useEffect } from 'react';
import * as d3 from 'd3';

/**
 * Custom hook encapsulating D3 force-directed graph rendering.
 * Extracted for testability — can be mocked in unit tests.
 */
export default function useDungGraphRenderer(svgRef, containerRef, data, activeExtension, getExtMembership, argTextMap, setTooltip) {
  useEffect(() => {
    if (!svgRef.current || !containerRef.current || !data.arguments || data.arguments.length === 0) return;

    const width = containerRef.current.clientWidth || 600;
    const height = 450;

    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    svg.append('defs').append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 24)
      .attr('refY', 0)
      .attr('markerWidth', 8)
      .attr('markerHeight', 8)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#64748b');

    const links = (data.attacks || []).map((a) => ({ source: a.from, target: a.to }));
    const nodes = data.arguments.map((a) => ({
      id: a.id, label: a.label || a.id, ext: getExtMembership(a.id),
    }));

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id((d) => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide(28));

    const link = svg.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('class', 'dung-edge');

    const node = svg.append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('class', (d) => `dung-node dung-ext-${d.ext}`)
      .call(d3.drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
      );

    node.append('circle').attr('r', 18);
    node.append('text').text((d) => d.label);

    node.on('mouseenter', (event, d) => {
      const text = argTextMap[d.id] || d.id;
      setTooltip({ show: true, x: event.offsetX + 10, y: event.offsetY - 10, content: `${d.id}: ${text}` });
    }).on('mouseleave', () => {
      setTooltip({ show: false, x: 0, y: 0, content: '' });
    });

    svg.call(d3.zoom()
      .scaleExtent([0.3, 3])
      .on('zoom', (event) => {
        svg.select('g').attr('transform', event.transform);
        link.attr('transform', event.transform);
        node.attr('transform', event.transform);
      })
    );

    simulation.on('tick', () => {
      link.attr('x1', (d) => d.source.x).attr('y1', (d) => d.source.y)
          .attr('x2', (d) => d.target.x).attr('y2', (d) => d.target.y);
      node.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    return () => simulation.stop();
  }, [data, activeExtension, getExtMembership, argTextMap, setTooltip]);
}
