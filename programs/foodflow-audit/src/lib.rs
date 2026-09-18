use anchor_lang::prelude::*;

declare_id!(FoodF1owAudit1111111111111111111111111111111);

#[program]
pub mod foodflow_audit {
    use super::*;

    /// 1. Initialize restaurant on-chain audit registry
    pub fn initialize_restaurant_registry(
        ctx: Context<InitializeRegistry>,
        restaurant_name: String,
        branch_id: String,
    ) -> Result<()> {
        let registry = &mut ctx.accounts.registry;
        registry.authority = ctx.accounts.authority.key();
        registry.restaurant_name = restaurant_name;
        registry.branch_id = branch_id;
        registry.total_batches_notarized = 0;
        registry.total_po_notarized = 0;
        registry.created_at = Clock::get()?.unix_timestamp;
        
        msg!(FoodFlow AI Registry Initialized for Branch: {}, registry.branch_id);
        Ok(())
    }

    /// 2. WEB3 FEATURE 1: Record & Notarize Ingredient Batch (FEFO Food Safety)
    pub fn record_ingredient_batch(
        ctx: Context<RecordBatch>,
        batch_code: String,
        ingredient_id: String,
        ingredient_name: String,
        record_hash: [u8; 32], // Deterministic SHA-256 Hash
        quantity: f64,
        expiry_timestamp: i64,
    ) -> Result<()> {
        let batch_record = &mut ctx.accounts.batch_record;
        let registry = &mut ctx.accounts.registry;

        batch_record.authority = ctx.accounts.authority.key();
        batch_record.branch_id = registry.branch_id.clone();
        batch_record.batch_code = batch_code.clone();
        batch_record.ingredient_id = ingredient_id;
        batch_record.ingredient_name = ingredient_name;
        batch_record.record_hash = record_hash;
        batch_record.quantity = quantity;
        batch_record.expiry_timestamp = expiry_timestamp;
        batch_record.notarized_at = Clock::get()?.unix_timestamp;

        registry.total_batches_notarized = registry.total_batches_notarized.checked_add(1).unwrap();

        emit!(BatchNotarizedEvent {
            branch_id: registry.branch_id.clone(),
            batch_code,
            record_hash,
            notarized_at: batch_record.notarized_at,
        });

        msg!(Ingredient Batch Notarized on Solana Devnet: {}, batch_record.batch_code);
        Ok(())
    }

    /// 3. WEB3 FEATURE 2: Record & Notarize AI Purchase Order (Tamper-evident PO Audit)
    pub fn record_ai_purchase_order(
        ctx: Context<RecordPurchaseOrder>,
        po_id: String,
        target_date: String,
        record_hash: [u8; 32], // Deterministic SHA-256 Hash of AI Recommendation + Approved Items
        total_estimated_cost: u64,
        ai_model_version: String,
    ) -> Result<()> {
        let po_record = &mut ctx.accounts.po_record;
        let registry = &mut ctx.accounts.registry;

        po_record.authority = ctx.accounts.authority.key();
        po_record.branch_id = registry.branch_id.clone();
        po_record.po_id = po_id.clone();
        po_record.target_date = target_date;
        po_record.record_hash = record_hash;
        po_record.total_estimated_cost = total_estimated_cost;
        po_record.ai_model_version = ai_model_version;
        po_record.notarized_at = Clock::get()?.unix_timestamp;

        registry.total_po_notarized = registry.total_po_notarized.checked_add(1).unwrap();

        emit!(PurchaseOrderNotarizedEvent {
            branch_id: registry.branch_id.clone(),
            po_id,
            record_hash,
            notarized_at: po_record.notarized_at,
        });

        msg!(AI Purchase Order Notarized on Solana Devnet: {}, po_record.po_id);
        Ok(())
    }

    /// 4. Verify Record Hash against On-chain State
    pub fn verify_record_hash(
        ctx: Context<VerifyBatch>,
        expected_hash: [u8; 32],
    ) -> Result<bool> {
        let batch_record = &ctx.accounts.batch_record;
        let is_valid = batch_record.record_hash == expected_hash;

        require!(is_valid, FoodFlowError::HashMismatch);

        emit!(AuditVerifiedEvent {
            batch_code: batch_record.batch_code.clone(),
            verified_hash: expected_hash,
            is_valid,
            verified_at: Clock::get()?.unix_timestamp,
        });

        Ok(is_valid)
    }
}

// ==========================================
// ACCOUNTS CONTEXTS (PDAs)
// ==========================================

#[derive(Accounts)]
#[instruction(restaurant_name: String, branch_id: String)]
pub struct InitializeRegistry<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + 32 + 64 + 32 + 8 + 8 + 8,
        seeds = [brestaurant_registry, branch_id.as_bytes()],
        bump
    )]
    pub registry: Account<'info, RestaurantRegistry>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(batch_code: String)]
pub struct RecordBatch<'info> {
    #[account(
        mut,
        seeds = [brestaurant_registry, registry.branch_id.as_bytes()],
        bump
    )]
    pub registry: Account<'info, RestaurantRegistry>,
    #[account(
        init,
        payer = authority,
        space = 8 + 32 + 32 + 64 + 32 + 64 + 32 + 8 + 8 + 8,
        seeds = [bbatch_audit, registry.branch_id.as_bytes(), batch_code.as_bytes()],
        bump
    )]
    pub batch_record: Account<'info, BatchAuditEntry>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(po_id: String)]
pub struct RecordPurchaseOrder<'info> {
    #[account(
        mut,
        seeds = [brestaurant_registry, registry.branch_id.as_bytes()],
        bump
    )]
    pub registry: Account<'info, RestaurantRegistry>,
    #[account(
        init,
        payer = authority,
        space = 8 + 32 + 32 + 64 + 32 + 32 + 8 + 32 + 8,
        seeds = [bpo_audit, registry.branch_id.as_bytes(), po_id.as_bytes()],
        bump
    )]
    pub po_record: Account<'info, PurchaseOrderAuditEntry>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct VerifyBatch<'info> {
    pub batch_record: Account<'info, BatchAuditEntry>,
}

// ==========================================
// STATE STRUCTS
// ==========================================

#[account]
pub struct RestaurantRegistry {
    pub authority: Pubkey,
    pub restaurant_name: String,
    pub branch_id: String,
    pub total_batches_notarized: u64,
    pub total_po_notarized: u64,
    pub created_at: i64,
}

#[account]
pub struct BatchAuditEntry {
    pub authority: Pubkey,
    pub branch_id: String,
    pub batch_code: String,
    pub ingredient_id: String,
    pub ingredient_name: String,
    pub record_hash: [u8; 32],
    pub quantity: f64,
    pub expiry_timestamp: i64,
    pub notarized_at: i64,
}

#[account]
pub struct PurchaseOrderAuditEntry {
    pub authority: Pubkey,
    pub branch_id: String,
    pub po_id: String,
    pub target_date: String,
    pub record_hash: [u8; 32],
    pub total_estimated_cost: u64,
    pub ai_model_version: String,
    pub notarized_at: i64,
}

// ==========================================
// EVENTS & ERRORS
// ==========================================

#[event]
pub struct BatchNotarizedEvent {
    pub branch_id: String,
    pub batch_code: String,
    pub record_hash: [u8; 32],
    pub notarized_at: i64,
}

#[event]
pub struct PurchaseOrderNotarizedEvent {
    pub branch_id: String,
    pub po_id: String,
    pub record_hash: [u8; 32],
    pub notarized_at: i64,
}

#[event]
pub struct AuditVerifiedEvent {
    pub batch_code: String,
    pub verified_hash: [u8; 32],
    pub is_valid: bool,
    pub verified_at: i64,
}

#[error_code]
pub enum FoodFlowError {
    #[msg(Provided hash does not match immutable on-chain record!)]
    HashMismatch,
}
