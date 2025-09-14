import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { AuthProvider } from '../AuthProvider'

// Mock Firebase auth
const mockAuth = {
  currentUser: null,
  onAuthStateChanged: vi.fn(),
}

vi.mock('../../services/firebase', () => ({
  auth: mockAuth,
}))

describe('AuthProvider', () => {
  it('renders children when provided', () => {
    render(
      <AuthProvider>
        <div data-testid="test-child">Test Child</div>
      </AuthProvider>
    )

    expect(screen.getByTestId('test-child')).toBeInTheDocument()
  })

  it('provides auth context to children', () => {
    const TestComponent = () => {
      return <div data-testid="auth-test">Auth Test</div>
    }

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    expect(screen.getByTestId('auth-test')).toBeInTheDocument()
  })
})
