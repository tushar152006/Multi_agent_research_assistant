import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function Card({ children, className = '', ...props }: CardProps) {
  return (
    <div className={`card card-padding ${className}`} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '', ...props }: CardProps) {
  return (
    <div className={`card-header ${className}`} style={{ marginBottom: 12 }} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className = '', ...props }: CardProps) {
  return (
    <h3 className={`card-title ${className}`} {...props}>
      {children}
    </h3>
  );
}

export function CardContent({ children, className = '', ...props }: CardProps) {
  return (
    <div className={`card-copy ${className}`} {...props}>
      {children}
    </div>
  );
}

export function Badge({ children, variant = 'default', className = '', ...props }: { children: React.ReactNode, variant?: 'default' | 'accent', className?: string } & React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span className={`pill ${className}`} {...props}>
      {children}
    </span>
  );
}
