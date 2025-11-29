public override void ProcessInteractable(XRInteractionUpdateOrder.UpdatePhase updatePhase)
{   
    // Dynamic is effectively just your normal Update().
    if (updatePhase == XRInteractionUpdateOrder.UpdatePhase.Dynamic)
    {
        NativeArray<Color32> data = texture.GetRawTextureData<Color32>();

        foreach (var interactor in interactorsSelecting)
        {
            // attachTransform will be the actual point of the touch interaction (e.g. index tip)
            // Most applications will probably just end up using this local touch position.
            Vector3 localTouchPosition = transform.InverseTransformPoint(interactor.GetAttachTransform(this).position);

            // For whiteboard drawing: compute UV coordinates on texture by flattening Vector3 against the plane and adding 0.5f.
            Vector2 uvTouchPosition = new Vector2(localTouchPosition.x + 0.5f, localTouchPosition.y + 0.5f);

            // Compute pixel coords as a fraction of the texture dimension
            Vector2 pixelCoordinate = Vector2.Scale(new Vector2(TextureSize, TextureSize), uvTouchPosition);

            // Have we seen this interactor before? If not, last position = current position.
            if (!lastPositions.TryGetValue(interactor, out Vector2 lastPosition))
            {
                lastPosition = pixelCoordinate;
            }

            // Very simple "line drawing algorithm".
            for (int i = 0; i < Vector2.Distance(pixelCoordinate, lastPosition); i++)
            {
                DrawSplat(Vector2.Lerp(lastPosition, pixelCoordinate, i / Vector2.Distance(pixelCoordinate, lastPosition)), data);
            }
            
            // Write/update the last-position.
            if (lastPositions.ContainsKey(interactor))
            {
                lastPositions[interactor] = pixelCoordinate;
            }
            else
            {
                lastPositions.Add(interactor, pixelCoordinate);
            }
        }

        texture.Apply(false);
    }
}