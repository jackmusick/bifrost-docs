interface LogoProps {
	type: "square" | "rectangle";
	className?: string;
	alt?: string;
}

/**
 * Logo component for Bifrost Docs
 * For rectangle type: shows icon + text
 * For square type: shows icon only
 */
export function Logo({ type, className = "", alt = "Bifrost Docs" }: LogoProps) {
	const defaultLogo = "/logo.svg";

	if (type === "rectangle") {
		return (
			<div className="flex items-center gap-2">
				<img src={defaultLogo} alt={alt} className="h-8 w-8" />
				<span className="hidden sm:inline-block font-semibold">
					Bifrost Docs
				</span>
			</div>
		);
	}

	// Square type - just the icon
	return <img src={defaultLogo} alt={alt} className={className || "h-10 w-10"} />;
}
