# Event Deletion Feature Analysis

## Executive Summary

**Question**: Should we add event deletion capability, and should it appear in the demo UI?

**Answer**: **YES** - Event deletion is a **P0 requirement** from the PRD (Section 6.4) that's currently missing. It should be implemented in both the API and the demo UI.

---

## 1. PRD Requirement Analysis

### PRD Section 6.4: Event Retrieval Endpoint (/inbox)

**Requirement:**
> "Support event acknowledgment/deletion to mark events as processed."

**Status**: ⚠️ **MISSING** - Currently identified as a gap in our implementation evaluation.

**Priority**: **P0 (Must-Have)**

---

## 2. Is Event Deletion Logical for Zapier API?

### ✅ **YES - Multiple Valid Reasons:**

#### 2.1 **Compliance Requirements (GDPR/CCPA)**
- **Right to be Forgotten**: Users must be able to delete their data
- **Data Subject Access Requests**: Users can request deletion of personal data
- **CCPA Compliance**: California privacy law requires deletion capabilities
- **Audit Requirements**: Ability to remove sensitive data from logs

#### 2.2 **Storage Cost Management**
- Events accumulate over time (even with TTL)
- Users may want to clean up old events manually
- Reduces DynamoDB storage costs
- Prevents unnecessary data retention

#### 2.3 **Testing and Debugging**
- Developers need to clean up test events
- Remove events that were created during development
- Clear inbox for fresh testing
- Debug workflow issues by removing problematic events

#### 2.4 **Workflow Management**
- Mark events as "processed" by deleting them
- Clean up successfully delivered events
- Remove failed events that won't be retried
- Manage inbox size for better performance

#### 2.5 **Real-World Use Cases**
- Customer requests data deletion
- Compliance audits require data removal
- Clean up after testing integrations
- Remove sensitive events (PII, financial data)

---

## 3. Implementation Requirements

### 3.1 Backend Implementation

#### **Step 1: Add Delete Method to EventStorageService**

**File**: `app/services/event_storage.py`

**New Method:**
```python
async def delete_event(
    self,
    customer_id: str,
    event_id: str,
) -> bool:
    """
    Delete an event from DynamoDB.
    
    Args:
        customer_id: Customer identifier (for security)
        event_id: Unique event identifier
        
    Returns:
        True if successfully deleted, False otherwise
    """
    if not self.table:
        return False
    
    try:
        # Verify event belongs to customer before deletion
        event = await self.get_event(customer_id, event_id)
        if not event:
            logger.warning(f"Event not found or doesn't belong to customer: {event_id}")
            return False
        
        # Delete the event
        self.table.delete_item(
            Key={
                "customer_id": customer_id,
                "event_id": event_id,
            }
        )
        
        logger.info(f"Event deleted: {event_id} for customer {customer_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting event from DynamoDB: {e}")
        return False
```

**Security Considerations:**
- ✅ Verify `customer_id` matches (prevent cross-customer deletion)
- ✅ Check event exists before deletion
- ✅ Log deletion for audit trail

#### **Step 2: Add DELETE Endpoint to Inbox API**

**File**: `app/api/inbox.py`

**New Endpoint:**
```python
@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Event not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Delete Event",
    description="Delete an event by ID. Only the event owner can delete their events.",
)
async def delete_event(
    event_id: str,
    customer_id: str = Depends(get_customer_id_from_api_key),
):
    """
    Delete an event.
    
    Args:
        event_id: Event identifier
        customer_id: Customer ID from authentication
        
    Returns:
        204 No Content on success
        
    Raises:
        HTTPException: If event not found or deletion fails
    """
    try:
        deleted = await event_storage.delete_event(
            customer_id=customer_id,
            event_id=event_id,
        )
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found or you don't have permission to delete it.",
            )
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting event: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the event.",
        )
```

**API Design:**
- **Route**: `DELETE /api/v1/inbox/{event_id}`
- **Response**: `204 No Content` (standard REST pattern)
- **Authentication**: Required (API key)
- **Authorization**: Customer can only delete their own events

#### **Step 3: Update Demo Backend (Optional)**

**File**: `demo/app.py`

If the demo backend needs to proxy delete requests:
```python
@app.delete("/demo/inbox/{event_id}")
async def delete_event_endpoint(event_id: str):
    """Delete event via demo backend (proxies to production API)."""
    if not TRIGGERS_API_URL or not TRIGGERS_API_KEY:
        raise ValueError("TRIGGERS_API_URL and TRIGGERS_API_KEY must be set")
    
    headers = {"Authorization": f"Bearer {TRIGGERS_API_KEY}"}
    url = f"{TRIGGERS_API_URL}/api/v1/inbox/{event_id}"
    
    try:
        response = requests.delete(url, headers=headers, timeout=10)
        response.raise_for_status()
        return Response(status_code=204)
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to delete event: {str(e)}",
        )
```

### 3.2 Frontend Implementation

#### **Step 1: Add Delete Function**

**File**: `frontend/src/App.jsx`

**New Function:**
```javascript
const deleteEvent = async (eventId) => {
  if (!confirm('Are you sure you want to delete this event?')) {
    return
  }

  try {
    setLoading(true)
    setError(null)

    const response = await fetch(`${DEMO_API_URL}/demo/inbox/${eventId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || errorData.message || 'Failed to delete event')
    }

    setSuccess('Event deleted successfully')
    
    // Reload events after a short delay
    setTimeout(() => {
      loadEvents()
    }, 500)
  } catch (err) {
    setError(`Failed to delete event: ${err.message}`)
  } finally {
    setLoading(false)
  }
}
```

#### **Step 2: Add Delete Button to Event List**

**File**: `frontend/src/App.jsx` (in the inbox tab section)

**Update Event Card:**
```jsx
{events.map((event) => (
  <div
    key={event.event_id}
    className="border border-zapier-gray-200 rounded-md p-4 hover:border-zapier-gray-300 hover:shadow-sm transition-all bg-white"
  >
    <div className="flex justify-between items-start mb-3">
      <div className="flex-1">
        <div className="font-mono text-sm font-semibold text-zapier-gray-900 mb-1">
          {event.event_id}
        </div>
        <div className="text-xs text-zapier-gray-500">
          {formatTimestamp(event.timestamp)}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
          event.status === 'delivered' ? 'bg-green-100 text-green-800' :
          event.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
          event.status === 'failed' ? 'bg-red-100 text-red-800' :
          'bg-zapier-gray-100 text-zapier-gray-700'
        }`}>
          {event.status || 'unknown'}
        </span>
        <button
          onClick={() => deleteEvent(event.event_id)}
          disabled={loading}
          className="px-3 py-1 text-xs text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md border border-red-200 hover:border-red-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title="Delete event"
        >
          Delete
        </button>
      </div>
    </div>
    {/* ... rest of event card ... */}
  </div>
))}
```

**UI Design Considerations:**
- Delete button should be clearly visible but not prominent
- Use red color to indicate destructive action
- Add confirmation dialog to prevent accidental deletions
- Show loading state while deleting
- Update UI immediately after successful deletion

---

## 4. Should It Show on the Demo UI?

### ✅ **YES - Strong Reasons:**

#### 4.1 **Demonstrates Full API Capabilities**
- Shows complete CRUD operations (Create, Read, Delete)
- Demonstrates the full feature set
- Proves the API is production-ready

#### 4.2 **Common User Expectation**
- Users expect to be able to delete items in lists
- Standard pattern in event management UIs
- Improves user experience

#### 4.3 **Testing and Demo Value**
- Allows users to clean up test events
- Demonstrates compliance features (GDPR/CCPA)
- Shows data management capabilities

#### 4.4 **Real-World Use Case**
- Matches how production systems work
- Shows practical utility
- Demonstrates security (customer isolation)

### 4.5 **UI Placement Recommendation**

**Best Location**: In the Event Inbox tab, next to each event card

**Design Pattern:**
```
┌─────────────────────────────────────────┐
│ Event ID: abc-123...                    │
│ Timestamp: 2024-01-15 10:30:00         │
│ Status: [delivered]  [Delete Button]  │
│                                         │
│ [View Payload ▼]                        │
└─────────────────────────────────────────┘
```

**Alternative**: Bulk delete option (future enhancement)
- Checkbox selection
- "Delete Selected" button
- Useful for cleaning up multiple events

---

## 5. Implementation Checklist

### Backend Tasks

- [ ] Add `delete_event()` method to `EventStorageService`
- [ ] Add `DELETE /api/v1/inbox/{event_id}` endpoint
- [ ] Add proper error handling (404, 403, 500)
- [ ] Add security checks (customer_id verification)
- [ ] Add logging for audit trail
- [ ] Update API documentation (OpenAPI/Swagger)
- [ ] Add unit tests for delete functionality
- [ ] Add integration tests

### Frontend Tasks

- [ ] Add `deleteEvent()` function
- [ ] Add delete button to event cards
- [ ] Add confirmation dialog
- [ ] Add loading states
- [ ] Add success/error messages
- [ ] Update event list after deletion
- [ ] Handle edge cases (network errors, etc.)

### Demo Backend Tasks (Optional)

- [ ] Add `DELETE /demo/inbox/{event_id}` proxy endpoint
- [ ] Handle errors gracefully
- [ ] Return appropriate status codes

### Documentation Tasks

- [ ] Update API documentation
- [ ] Add deletion examples
- [ ] Document security considerations
- [ ] Update architecture summary
- [ ] Update implementation evaluation

---

## 6. Security Considerations

### 6.1 **Customer Isolation**
- ✅ Verify `customer_id` matches before deletion
- ✅ Prevent cross-customer deletion attempts
- ✅ Return 404 (not 403) to avoid information leakage

### 6.2 **Audit Logging**
- ✅ Log all deletion attempts
- ✅ Include customer_id, event_id, timestamp
- ✅ Log success and failure cases

### 6.3 **Rate Limiting**
- ✅ Apply rate limiting to delete endpoints
- ✅ Prevent abuse (mass deletion attacks)
- ✅ Consider separate limits for deletion vs. creation

### 6.4 **Soft Delete Option (Future)**
- Consider soft delete (mark as deleted, don't remove)
- Allows recovery if needed
- Better for compliance audits
- Can implement later if needed

---

## 7. Testing Requirements

### 7.1 **Unit Tests**
- Test successful deletion
- Test deletion of non-existent event
- Test deletion of another customer's event
- Test error handling

### 7.2 **Integration Tests**
- Test full flow: create → retrieve → delete
- Test authentication requirements
- Test customer isolation

### 7.3 **UI Tests**
- Test delete button click
- Test confirmation dialog
- Test UI update after deletion
- Test error handling in UI

---

## 8. Estimated Effort

### Backend Implementation
- **Time**: 2-3 hours
- **Complexity**: Low (straightforward DynamoDB delete)
- **Risk**: Low (well-understood operation)

### Frontend Implementation
- **Time**: 1-2 hours
- **Complexity**: Low (standard React patterns)
- **Risk**: Low (simple UI addition)

### Testing
- **Time**: 1-2 hours
- **Complexity**: Low
- **Risk**: Low

### **Total Estimated Effort**: 4-7 hours

---

## 9. Conclusion

### ✅ **Recommendation: IMPLEMENT**

**Reasons:**
1. **PRD Requirement**: P0 requirement currently missing
2. **Compliance**: Needed for GDPR/CCPA compliance
3. **User Experience**: Standard feature users expect
4. **Low Effort**: Straightforward implementation
5. **High Value**: Completes the API feature set

### **Priority: HIGH**

This should be implemented before launch to meet P0 requirements and provide a complete, production-ready API.

### **UI Inclusion: YES**

The delete functionality should definitely appear in the demo UI to:
- Demonstrate the complete API
- Show compliance features
- Provide practical utility for testing
- Match user expectations

---

## 10. Next Steps

1. **Implement Backend** (delete method + endpoint)
2. **Implement Frontend** (delete button + confirmation)
3. **Add Tests** (unit + integration)
4. **Update Documentation**
5. **Deploy and Test**

This is a straightforward feature that will significantly improve the completeness and usability of the API.

