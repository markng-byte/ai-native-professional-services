// ModuleErrorBoundary.tsx — Per-module error boundary for AEGIS
// Prevents one module failure from crashing the entire shell

import React from 'react'

const C = {
  bg:    '#07100e',
  bg2:   '#0b1a16',
  teal:  '#3de8a0',
  red:   '#f05060',
  muted: '#5a8878',
  dim:   '#2a5040',
  border:'rgba(61,232,160,0.12)',
}

interface Props {
  moduleName: string
  moduleColor: string
  children: React.ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ModuleErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error(`[AEGIS] Module ${this.props.moduleName} crashed:`, error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          height: '100%', gap: 20,
          background: C.bg, padding: 40,
        }}>
          {/* Icon */}
          <div style={{
            width: 56, height: 56, borderRadius: '50%',
            border: `2px solid ${C.red}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 24, color: C.red,
            boxShadow: `0 0 24px ${C.red}44`,
          }}>⚠</div>

          {/* Module name */}
          <div style={{
            color: this.props.moduleColor,
            fontSize: 13, letterSpacing: 3, fontWeight: 700,
          }}>{this.props.moduleName}</div>

          {/* Error message */}
          <div style={{
            color: C.muted, fontSize: 12, textAlign: 'center', maxWidth: 420,
          }}>
            This module encountered an error and could not render.
            Other modules are unaffected.
          </div>

          {/* Error detail */}
          {this.state.error && (
            <div style={{
              background: C.bg2, border: `1px solid ${C.border}`,
              borderRadius: 6, padding: '10px 16px',
              fontFamily: 'Courier New, monospace', fontSize: 11,
              color: C.red, maxWidth: 500, wordBreak: 'break-word',
            }}>
              {this.state.error.message}
            </div>
          )}

          {/* Retry button */}
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{
              background: 'none',
              border: `1px solid ${this.props.moduleColor}`,
              borderRadius: 4, color: this.props.moduleColor,
              fontSize: 11, letterSpacing: 2, padding: '8px 20px',
              cursor: 'pointer', transition: 'all 0.15s',
            }}
          >
            ↺ RETRY MODULE
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
