import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function Card({ children, className = '', ...props }: CardProps) {
  return (
    <div className={`glass-panel ${className}`} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '', ...props }: CardProps) {
  return (
    <div className={`panel-header ${className}`} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className = '', ...props }: CardProps) {
  return (
    <h3 className={className} {...props}>
      {children}
    </h3>
  );
}

export function CardContent({ children, className = '', ...props }: CardProps) {
  return (
    <div className={className} {...props}>
      {children}
    </div>
  );
}

export function Badge({ children, variant = 'default', className = '', ...props }: { children: React.ReactNode, variant?: 'default' | 'accent', className?: string } & React.HTMLAttributes<HTMLSpanElement>) {
  const variantClass = variant === 'accent' ? 'badge-accent' : '';
  return (
    <span className={`badge ${variantClass} ${className}`} {...props}>
      {children}
    </span>
  );
}
