/**
 * Tests for the SidePanel component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import SidePanel from '../SidePanel';
import { useStore, useSelectedNode } from '../../store/useStore';
import { EntityType, RelationType } from '../../types/core';

// Mock framer-motion
vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
        aside: ({ children, ...props }: any) => <aside {...props}>{children}</aside>,
    },
    AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Mock fetch
global.fetch = vi.fn();

const mockSelectedNode = {
    id: 'test-node-1',
    name: 'Test Node',
    type: 'Concept',
    salience: 0.8,
    summary: 'This is a test node for demonstration',
    aliases: ['Test', 'Demo Node'],
    evidence_count: 3,
    size: 17.6,
    color: '#3b82f6',
    selected: true,
    highlighted: false,
};

const mockStore = {
    sidePanelContent: 'node-details' as const,
    searchResults: [],
    currentQuestion: '',
    currentAnswer: '',
    currentCitations: [],
    upsertNodes: vi.fn(),
    upsertEdges: vi.fn(),
    edges: new Map(),
};

// Mock the store hooks
vi.mock('../../store/useStore', () => ({
    useStore: vi.fn(),
    useSelectedNode: vi.fn(),
}));

describe('SidePanel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useStore).mockReturnValue(mockStore);
        vi.mocked(useSelectedNode).mockReturnValue(mockSelectedNode);
    });

    it('renders when open', () => {
        render(<SidePanel isOpen={true} onClose={vi.fn()} />);
        expect(screen.getAllByText('Test Node')).toHaveLength(2); // Header and content
    });

    it('does not render when closed', () => {
        render(<SidePanel isOpen={false} onClose={vi.fn()} />);
        expect(screen.queryByText('Test Node')).not.toBeInTheDocument();
    });

    it('displays node details correctly', () => {
        render(<SidePanel isOpen={true} onClose={vi.fn()} />);

        expect(screen.getAllByText('Test Node')).toHaveLength(2); // Header and content
        expect(screen.getByText('Concept')).toBeInTheDocument();
        expect(screen.getByText('80.0%')).toBeInTheDocument();
        expect(screen.getByText('This is a test node for demonstration')).toBeInTheDocument();
        expect(screen.getByText('Test, Demo Node')).toBeInTheDocument();
    });

    it('shows evidence quotes when available', () => {
        const mockEdges = new Map();
        mockEdges.set('edge-1', {
            id: 'edge-1',
            source: 'test-node-1',
            target: 'other-node',
            predicate: 'relates_to',
            confidence: 0.9,
            evidence_count: 1,
            evidence: [{
                doc_id: 'test-doc',
                quote: 'This is test evidence for the relationship',
                offset: 0,
            }],
        });

        // Update the mock implementation for this test
        vi.mocked(useStore).mockReturnValue({
            ...mockStore,
            edges: mockEdges,
        });

        render(<SidePanel isOpen={true} onClose={vi.fn()} />);

        expect(screen.getByText('"This is test evidence for the relationship"')).toBeInTheDocument();
        expect(screen.getByText('Source: test-doc')).toBeInTheDocument();
        expect(screen.getByText('relates_to')).toBeInTheDocument();
        expect(screen.getByText('Confidence: 90.0%')).toBeInTheDocument();
    });

    it('shows message when no evidence is available', () => {
        render(<SidePanel isOpen={true} onClose={vi.fn()} />);

        expect(screen.getByText('No evidence quotes available. Expand the neighborhood to load relationships with evidence.')).toBeInTheDocument();
    });

    it('handles expand neighborhood button click', async () => {
        const mockResponse = {
            center_node: mockSelectedNode,
            neighbors: [],
            relationships: [],
            total_neighbors: 0,
            processing_time: 0.1,
        };

        (global.fetch as any).mockResolvedValueOnce({
            ok: true,
            json: async () => mockResponse,
        });

        render(<SidePanel isOpen={true} onClose={vi.fn()} />);

        const expandButton = screen.getByText('Expand 1-hop Neighborhood');
        fireEvent.click(expandButton);

        expect(screen.getByText('Expanding...')).toBeInTheDocument();

        await waitFor(() => {
            expect(mockStore.upsertNodes).toHaveBeenCalledWith([]);
            expect(mockStore.upsertEdges).toHaveBeenCalledWith([]);
        });
    });

    it('handles expand neighborhood error', async () => {
        (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

        render(<SidePanel isOpen={true} onClose={vi.fn()} />);

        const expandButton = screen.getByText('Expand 1-hop Neighborhood');
        fireEvent.click(expandButton);

        await waitFor(() => {
            expect(screen.getByText('Network error')).toBeInTheDocument();
        });
    });

    it('calls onClose when close button is clicked', () => {
        const onClose = vi.fn();
        render(<SidePanel isOpen={true} onClose={onClose} />);

        const closeButton = screen.getByLabelText('Close panel');
        fireEvent.click(closeButton);

        expect(onClose).toHaveBeenCalled();
    });

    it('truncates long evidence quotes', () => {
        const longQuote = 'A'.repeat(250);
        const mockEdges = new Map();
        mockEdges.set('edge-1', {
            id: 'edge-1',
            source: 'test-node-1',
            target: 'other-node',
            predicate: 'relates_to',
            confidence: 0.9,
            evidence_count: 1,
            evidence: [{
                doc_id: 'test-doc',
                quote: longQuote,
                offset: 0,
            }],
        });

        vi.mocked(useStore).mockReturnValue({
            ...mockStore,
            edges: mockEdges,
        });

        render(<SidePanel isOpen={true} onClose={vi.fn()} />);

        expect(screen.getByText(`"${'A'.repeat(200)}..."`)).toBeInTheDocument();
    });
});