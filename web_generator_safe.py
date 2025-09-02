#!/usr/bin/env python3
"""
Safe wrapper for web_generator with comprehensive error handling and logging.
"""

import os
import sys
import traceback
from typing import List, Optional

# Import the original web_generator
from web_generator import generate_all_pages as original_generate_all_pages
from web_generator import (
    create_index_page,
    create_folder_page,
    create_timestamp_page,
    create_trends_page,
    create_directory_structure,
    discover_folders_from_ini_files
)

# Import logging utilities
from web_logging import (
    setup_logging,
    get_logger,
    DataValidationError,
    FileOperationError,
    validate_directory,
    validate_timestamp,
    ErrorRecovery,
    create_error_page,
    safe_write_file,
    log_performance_metrics
)


def safe_generate_all_pages(
    work_dir: str,
    web_output_dir: str,
    folders: Optional[List[str]] = None,
    log_file: Optional[str] = None,
    log_level: str = "INFO"
) -> bool:
    """
    Safely generate all web pages with comprehensive error handling and logging.
    
    Args:
        work_dir: Base work directory with data
        web_output_dir: Output directory for web pages
        folders: List of folder names to process (if None, will be auto-discovered)
        log_file: Optional path to log file
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        True if generation was successful, False otherwise
    """
    # Set up logging
    if log_file is None:
        log_file = os.path.join(web_output_dir, 'web_generation.log')
    
    logger = setup_logging(log_level, log_file)
    logger.info("=" * 60)
    logger.info("Starting Quokka Regression Testing Web Generation")
    logger.info("=" * 60)
    logger.info(f"Work directory: {work_dir}")
    logger.info(f"Output directory: {web_output_dir}")
    logger.info(f"Log file: {log_file}")
    
    success = False
    
    try:
        # Validate input directories
        logger.info("Validating directories...")
        validate_directory(work_dir)
        validate_directory(web_output_dir, create=True)
        
        # Discover folders if not provided
        if folders is None:
            logger.info("Discovering folders from INI files...")
            try:
                folders = discover_folders_from_ini_files(work_dir)
                if not folders:
                    raise DataValidationError("No folders found in INI files")
                logger.info(f"Discovered {len(folders)} folders: {', '.join(folders)}")
            except Exception as e:
                logger.error(f"Failed to discover folders: {e}")
                raise
        else:
            logger.info(f"Using provided folders: {', '.join(folders)}")
        
        # Validate folders exist
        valid_folders = []
        for folder in folders:
            folder_path = os.path.join(work_dir, folder)
            if os.path.exists(folder_path):
                valid_folders.append(folder)
            else:
                logger.warning(f"Folder does not exist, skipping: {folder_path}")
        
        if not valid_folders:
            raise DataValidationError("No valid folders to process")
        
        logger.info(f"Processing {len(valid_folders)} valid folders")
        
        # Create directory structure
        with ErrorRecovery("directory structure creation"):
            logger.info("Creating directory structure...")
            create_directory_structure(web_output_dir, valid_folders)
        
        # Generate pages with individual error handling
        generation_stats = {
            'total_folders': len(valid_folders),
            'successful_folders': 0,
            'failed_folders': 0,
            'total_pages': 0,
            'failed_pages': 0
        }
        
        # Create main index page
        try:
            logger.info("Creating main index page...")
            create_index_page(work_dir, web_output_dir, valid_folders)
            generation_stats['total_pages'] += 1
            logger.info("Successfully created main index page")
        except Exception as e:
            logger.error(f"Failed to create main index page: {e}")
            logger.debug(traceback.format_exc())
            generation_stats['failed_pages'] += 1
            
            # Create error page as fallback
            error_html = create_error_page(
                "Failed to generate main index page",
                str(e) if log_level == "DEBUG" else None
            )
            index_path = os.path.join(web_output_dir, 'index.html')
            safe_write_file(index_path, error_html, backup=False)
        
        # Process each folder
        for folder in valid_folders:
            folder_path = os.path.join(work_dir, folder)
            folder_success = True
            
            logger.info(f"Processing folder: {folder}")
            
            try:
                # Create folder index page
                logger.debug(f"Creating folder index for {folder}...")
                create_folder_page(work_dir, web_output_dir, folder)
                generation_stats['total_pages'] += 1
                
                # Get performance test directory
                perf_test_dir = os.path.join(folder_path, 'performance_test')
                if os.path.exists(perf_test_dir):
                    # Get all timestamp directories
                    timestamps = sorted([
                        d for d in os.listdir(perf_test_dir)
                        if os.path.isdir(os.path.join(perf_test_dir, d)) and d.isdigit()
                    ], reverse=True)
                    
                    # Create timestamp pages
                    for timestamp in timestamps:
                        try:
                            # Validate timestamp format
                            validate_timestamp(timestamp)
                            
                            logger.debug(f"Creating timestamp page for {folder}/{timestamp}...")
                            create_timestamp_page(work_dir, web_output_dir, folder, timestamp)
                            generation_stats['total_pages'] += 1
                        except DataValidationError as e:
                            logger.warning(f"Invalid timestamp {timestamp}: {e}")
                            generation_stats['failed_pages'] += 1
                        except Exception as e:
                            logger.error(f"Failed to create timestamp page {folder}/{timestamp}: {e}")
                            generation_stats['failed_pages'] += 1
                            folder_success = False
                
                # Create trends page
                try:
                    logger.debug(f"Creating trends page for {folder}...")
                    create_trends_page(work_dir, web_output_dir, folder)
                    generation_stats['total_pages'] += 1
                except Exception as e:
                    logger.error(f"Failed to create trends page for {folder}: {e}")
                    generation_stats['failed_pages'] += 1
                    folder_success = False
                
                if folder_success:
                    generation_stats['successful_folders'] += 1
                    logger.info(f"Successfully processed folder: {folder}")
                else:
                    generation_stats['failed_folders'] += 1
                    logger.warning(f"Partially failed processing folder: {folder}")
                    
            except Exception as e:
                logger.error(f"Failed to process folder {folder}: {e}")
                logger.debug(traceback.format_exc())
                generation_stats['failed_folders'] += 1
                
                # Create error page for folder
                error_html = create_error_page(
                    f"Failed to generate pages for folder: {folder}",
                    str(e) if log_level == "DEBUG" else None
                )
                folder_index_path = os.path.join(web_output_dir, folder, 'index.html')
                safe_write_file(folder_index_path, error_html, backup=False)
        
        # Log final statistics
        log_performance_metrics(generation_stats)
        
        # Determine overall success
        if generation_stats['failed_folders'] == 0 and generation_stats['failed_pages'] == 0:
            logger.info("Web generation completed successfully!")
            success = True
        elif generation_stats['successful_folders'] > 0:
            logger.warning(f"Web generation completed with errors: "
                         f"{generation_stats['failed_folders']} folders failed, "
                         f"{generation_stats['failed_pages']} pages failed")
            success = True  # Partial success
        else:
            logger.error("Web generation failed completely")
            success = False
            
    except KeyboardInterrupt:
        logger.warning("Web generation interrupted by user")
        success = False
    except Exception as e:
        logger.error(f"Fatal error during web generation: {e}")
        logger.debug(traceback.format_exc())
        success = False
        
        # Try to create a top-level error page
        try:
            error_html = create_error_page(
                "Fatal error during web generation",
                str(e) if log_level == "DEBUG" else None
            )
            index_path = os.path.join(web_output_dir, 'index.html')
            safe_write_file(index_path, error_html, backup=False)
        except:
            pass  # Last resort failed
    
    finally:
        logger.info("=" * 60)
        logger.info(f"Web generation finished - Success: {success}")
        logger.info("=" * 60)
    
    return success


def main():
    """
    Main entry point for standalone execution.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Quokka regression testing web pages')
    parser.add_argument('work_dir', help='Base work directory with data')
    parser.add_argument('web_output_dir', help='Output directory for web pages')
    parser.add_argument('--folders', nargs='+', help='Specific folders to process')
    parser.add_argument('--log-file', help='Path to log file')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Logging level')
    
    args = parser.parse_args()
    
    success = safe_generate_all_pages(
        args.work_dir,
        args.web_output_dir,
        args.folders,
        args.log_file,
        args.log_level
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()