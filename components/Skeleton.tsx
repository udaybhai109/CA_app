type SkeletonProps = {
  className?: string;
};

export default function Skeleton({ className = "h-4 w-full" }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-gray-200 transition-all duration-200 ease-in-out ${className}`}
      aria-hidden="true"
    />
  );
}
