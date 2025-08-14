/**
 * Tests for Graph3D component interactive features
 * Tests hover tooltips, click selection, and navigation controls
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { UINode, UIEdge } from '../../types/ui';

// Mock react-force-graph-3d
const mockCameraPosition = vi.fn();
const mockGraph2ScreenCoords = vi.fn();
const mockD3Force = vi.fn(() => ({
  distance: vi.fn().mockReturnThis(),
  strength: vi.fn().mockReturnThis(),
}));

vi.mock('react-force-graph-3d', () => ({
  default: React.forwardRef((props: any, ref: any) => {
    // Expose methods to ref for testing
    React.useImperativeHandle(ref, () => ({
      cameraPosition: mockCameraPosition,
      graph2ScreenCoords: mockGraph2ScreenCoords,
      d3Force: mockD3Force,
    }));

    return (
      <div data-testid="force-graph-3d">
        {/* Simulate nodes for interaction testing */}
        {props.graphData.nodes.map((node: UINode) => (
          <div
            key={node.id}
            data-testid={`node-${node.id}`}
            onMouseEnter={() => props.onNodeHover?.(node)}
            onMouseLeave={() => props.onNodeHover?.(null)}
            onClick={() => props.onNodeClick?.(node)}
          >
            {node.name}
          </div>
        ))}
      </div>
    );
  })
}));

// Mock fetch for API calls
global.fetch = vi.fn();

// Mock store
vi.mock('../../store/useStore', () => ({
  useStore: vi.fn(),
  useGraphData: vi.fn(),
}));

// Import after mocking
import Graph3D from '../Graph3D';
import { useStore, useGraphData } from '../../store/useStore';

// Mock graph data
const mockNode: UINode = {
  id: 'test-node-1',
  name: 'Test Node',
  type: 'Concept',
  salience: 0.8,
  summary: 'This is a test node for demonstration',
  aliases: ['Test', 'Demo Node'],
  evidence_count: 3,
  x: 100,
  y: 100,
  z: 100,
  color: '#3b82f6',
  size: 17.6, // 8 + 12 * 0.8
  selected: false,
  highlighted: false,
};

const mockEdge: UIEdge = {
  id: 'test-edge-1',
  source: 'test-node-1',
  target: 'test-node-2',
  predicate: 'relates_to',
  confidence: 0.9,
  evidence_count: 2,
  width: 2.75, // 0.5 + 2.5 * 0.9
  color: '#10b981',
  opacity: 0.86,
  selected: false,
};

const mockGraphData = {
  nodes: [mockNode],
  links: [mockEdge],
};

const mockStore = {
  selectNode: vi.fn(),
  isConnected: true,
  highlightNodes: vi.fn(),
  clearHighlights: vi.fn(),
  setCameraPosition: vi.fn(),
  setCameraTarget: vi.fn(),
};

const mockUseStore = vi.mocked(useStore);
const mockUseGraphData = vi.mocked(useGraphData);

describe('Graph3D Interactive Features', () => {
  beforeEach(() => {
    mockCameraPosition.mockClear();
    mockGraph2ScreenCoords.mockClear();
    mockStore.selectNode.mockClear();
    mockStore.clearHighlights.mockClear();
    mockStore.setCameraPosition.mockClear();
    mockStore.setCameraTarget.mockClear();
    
    // Setup default mocks
    mockUseStore.mockReturnValue(mockStore);
    mockUseGraphData.mockReturnValue(mockGraphData);
    
    // Mock successful API response
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ nodes: [], edges: [] }),
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Hover Tooltips (Requirement 2.3)', () => {
    it('should display tooltip on node hover with correct information', async () => {
      mockGraph2ScreenCoords.mockReturnValue({ x: 200, y: 150 });
      
      render(<Graph3D />);
      
      const nodeElement = screen.getByTestId('node-test-node-1');
      
      // Hover over node
      fireEvent.mouseEnter(nodeElement);
      
      await waitFor(() => {
        expect(screen.getAllByText('Test Node')).toHaveLength(2); // Node and tooltip
        expect(screen.getByText(/Type: Concept/)).toBeInTheDocument();
        expect(screen.getByText(/Salience: 80.0%/)).toBeInTheDocument();
        expect(screen.getByText('This is a test node for demonstration')).toBeInTheDocument();
        expect(screen.getByText('3 evidence sources')).toBeInTheDocument();
      });
    });

    it('should hide tooltip when mouse leaves node', async () => {
      mockGraph2ScreenCoords.mockReturnValue({ x: 200, y: 150 });
      
      render(<Graph3D />);
      
      const nodeElement = screen.getByTestId('node-test-node-1');
      
      // Hover over node
      fireEvent.mouseEnter(nodeElement);
      
      await waitFor(() => {
        expect(screen.getAllByText('Test Node')).toHaveLength(2); // Node and tooltip
      });
      
      // Leave node
      fireEvent.mouseLeave(nodeElement);
      
      await waitFor(() => {
        expect(screen.getAllByText('Test Node')).toHaveLength(1); // Only node, no tooltip
      });
    });

    it('should position tooltip correctly relative to node', async () => {
      const mockCoords = { x: 300, y: 200 };
      mockGraph2ScreenCoords.mockReturnValue(mockCoords);
      
      render(<Graph3D />);
      
      const nodeElement = screen.getByTestId('node-test-node-1');
      fireEvent.mouseEnter(nodeElement);
      
      await waitFor(() => {
        // Find the tooltip by its specific class
        const tooltip = document.querySelector('.absolute.pointer-events-none.z-50');
        expect(tooltip).toHaveStyle({
          left: '310px', // x + 10
          top: '190px',  // y - 10
        });
      });
    });
  });

  describe('Click Selection and Highlighting (Requirement 2.4)', () => {
    it('should select node and expand neighborhood on click', async () => {
      render(<Graph3D />);
      
      const nodeElement = screen.getByTestId('node-test-node-1');
      
      // Click on node
      fireEvent.click(nodeElement);
      
      await waitFor(() => {
        // Should clear highlights
        expect(mockStore.clearHighlights).toHaveBeenCalled();
        
        // Should select the node
        expect(mockStore.selectNode).toHaveBeenCalledWith('test-node-1');
        
        // Should call API to expand neighborhood
        expect(global.fetch).toHaveBeenCalledWith('/api/neighbors?node_id=test-node-1&hops=1&limit=200');
      });
    });

    it('should center camera on selected node', async () => {
      render(<Graph3D />);
      
      const nodeElement = screen.getByTestId('node-test-node-1');
      fireEvent.click(nodeElement);
      
      await waitFor(() => {
        expect(mockCameraPosition).toHaveBeenCalledWith(
          { x: 300, y: 300, z: 300 }, // node position + distance (200)
          { x: 100, y: 100, z: 100 }, // node position
          1000 // animation duration
        );
        
        expect(mockStore.setCameraPosition).toHaveBeenCalledWith({
          x: 300, y: 300, z: 300
        });
        
        expect(mockStore.setCameraTarget).toHaveBeenCalledWith({
          x: 100, y: 100, z: 100
        });
      });
    });

    it('should handle API errors gracefully', async () => {
      // Mock API failure
      (global.fetch as any).mockRejectedValue(new Error('Network error'));
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      render(<Graph3D />);
      
      const nodeElement = screen.getByTestId('node-test-node-1');
      fireEvent.click(nodeElement);
      
      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Failed to expand node neighborhood:', expect.any(Error));
      });
      
      consoleSpy.mockRestore();
    });
  });

  describe('Graph Navigation Controls', () => {
    it('should render navigation control buttons', () => {
      render(<Graph3D />);
      
      expect(screen.getByTitle('Zoom In')).toBeInTheDocument();
      expect(screen.getByTitle('Zoom Out')).toBeInTheDocument();
      expect(screen.getByTitle('Reset View')).toBeInTheDocument();
    });

    it('should reset view when reset button is clicked', () => {
      render(<Graph3D />);
      
      const resetButton = screen.getByTitle('Reset View');
      fireEvent.click(resetButton);
      
      expect(mockCameraPosition).toHaveBeenCalledWith(
        { x: 0, y: 0, z: 400 },
        { x: 0, y: 0, z: 0 },
        1000
      );
      
      expect(mockStore.setCameraPosition).toHaveBeenCalledWith({ x: 0, y: 0, z: 400 });
      expect(mockStore.setCameraTarget).toHaveBeenCalledWith({ x: 0, y: 0, z: 0 });
    });

    it('should zoom in when zoom in button is clicked', () => {
      // Mock current camera position
      mockCameraPosition.mockReturnValue({ x: 0, y: 0, z: 400 });
      
      render(<Graph3D />);
      
      const zoomInButton = screen.getByTitle('Zoom In');
      fireEvent.click(zoomInButton);
      
      // Should zoom in by factor of 0.8
      expect(mockCameraPosition).toHaveBeenCalledWith(
        { x: 0, y: 0, z: 320 }, // 400 * 0.8
        undefined,
        300
      );
      
      expect(mockStore.setCameraPosition).toHaveBeenCalledWith({ x: 0, y: 0, z: 320 });
    });

    it('should zoom out when zoom out button is clicked', () => {
      // Mock current camera position
      mockCameraPosition.mockReturnValue({ x: 0, y: 0, z: 400 });
      
      render(<Graph3D />);
      
      const zoomOutButton = screen.getByTitle('Zoom Out');
      fireEvent.click(zoomOutButton);
      
      // Should zoom out by factor of 1.25
      expect(mockCameraPosition).toHaveBeenCalledWith(
        { x: 0, y: 0, z: 500 }, // 400 * 1.25
        undefined,
        300
      );
      
      expect(mockStore.setCameraPosition).toHaveBeenCalledWith({ x: 0, y: 0, z: 500 });
    });

    it('should respect minimum zoom distance', () => {
      // Mock very close camera position
      mockCameraPosition.mockReturnValue({ x: 0, y: 0, z: 60 });
      
      render(<Graph3D />);
      
      const zoomInButton = screen.getByTitle('Zoom In');
      fireEvent.click(zoomInButton);
      
      // Should not zoom closer than minimum distance (50)
      expect(mockCameraPosition).toHaveBeenCalledWith(
        { x: 0, y: 0, z: 50 },
        undefined,
        300
      );
    });

    it('should respect maximum zoom distance', () => {
      // Mock very far camera position
      mockCameraPosition.mockReturnValue({ x: 0, y: 0, z: 1800 });
      
      render(<Graph3D />);
      
      const zoomOutButton = screen.getByTitle('Zoom Out');
      fireEvent.click(zoomOutButton);
      
      // Should not zoom farther than maximum distance (2000)
      expect(mockCameraPosition).toHaveBeenCalledWith(
        { x: 0, y: 0, z: 2000 },
        undefined,
        300
      );
    });
  });

  describe('Graph Statistics Display', () => {
    it('should display correct node and edge counts', () => {
      render(<Graph3D />);
      
      expect(screen.getByText('Nodes: 1')).toBeInTheDocument();
      expect(screen.getByText('Edges: 1')).toBeInTheDocument();
    });

    it('should display connection status', () => {
      render(<Graph3D />);
      
      expect(screen.getByText('Connected')).toBeInTheDocument();
      expect(screen.getByText('Connected')).toHaveClass('text-green-400');
    });

    it('should display disconnected status when not connected', () => {
      mockUseStore.mockReturnValue({
        ...mockStore,
        isConnected: false,
      });
      
      render(<Graph3D />);
      
      expect(screen.getByText('Disconnected')).toBeInTheDocument();
      expect(screen.getByText('Disconnected')).toHaveClass('text-red-400');
    });
  });

  describe('Loading and Empty States', () => {
    it('should show loading state when not connected and no data', () => {
      mockUseStore.mockReturnValue({
        ...mockStore,
        isConnected: false,
      });
      
      // Mock empty graph data
      mockUseGraphData.mockReturnValue({ nodes: [], links: [] });
      
      render(<Graph3D />);
      
      expect(screen.getByText('Connecting to knowledge graph...')).toBeInTheDocument();
    });

    it('should show empty state when connected but no data', () => {
      // Mock empty graph data
      mockUseGraphData.mockReturnValue({ nodes: [], links: [] });
      
      render(<Graph3D />);
      
      expect(screen.getByText('No Knowledge Graph Data')).toBeInTheDocument();
      expect(screen.getByText('Ingest some text to start building your knowledge graph')).toBeInTheDocument();
    });
  });
});